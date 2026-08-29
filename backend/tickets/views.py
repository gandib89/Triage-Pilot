from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import Ticket, DecisionLog, TicketMessage
from .serializers import (
    TicketSerializer, TicketMessageSerializer, DecisionLogSerializer,
    DecisionLogDecideSerializer, CustomTokenObtainPairSerializer,
    CookieTokenRefreshSerializer,
    RegisterSerializer, VerifyOTPSerializer, ResendOTPSerializer,
)
from .agent import apply_triage, triage_in_background
from .otp import send_otp_email
from .throttles import LoginRateThrottle, RegisterRateThrottle, TriageRetryThrottle


def _set_refresh_cookie(response, refresh_str):
    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE_NAME, refresh_str,
        max_age=int(jwt_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        httponly=True, secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite='Strict', path=settings.REFRESH_TOKEN_COOKIE_PATH,
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, path=settings.REFRESH_TOKEN_COOKIE_PATH)


class IsSupportStaff(permissions.BasePermission):
    """Allows access only to authenticated agent/admin accounts."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        profile = getattr(user, 'profile', None)
        return bool(profile and profile.is_staff_role)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Same login flow as SimpleJWT's view, but the refresh token is moved
    out of the response body into an httpOnly cookie before it reaches the
    client — the access token is the only thing the SPA ever sees."""
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh = response.data.pop('refresh', None)
        if refresh:
            _set_refresh_cookie(response, refresh)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """POST /api/token/refresh/ — refresh token comes from the httpOnly
    cookie, not the body. See CookieTokenRefreshSerializer for the
    reuse-family revocation this adds on top of SimpleJWT's rotation."""
    serializer_class = CookieTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data={}, context={'request': request})
        serializer.is_valid(raise_exception=True)
        response = Response({'access': serializer.validated_data['access']},
                             status=status.HTTP_200_OK)
        if 'refresh' in serializer.validated_data:
            _set_refresh_cookie(response, serializer.validated_data['refresh'])
        return response


class LogoutView(APIView):
    """POST /api/logout/ — blacklists the current refresh token and clears
    its cookie. No-op (still 200) if there's no cookie to act on, so a
    double logout or an already-expired session isn't an error."""
    permission_classes = [AllowAny]

    def post(self, request):
        raw_token = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if raw_token:
            try:
                RefreshToken(raw_token).blacklist()
            except TokenError:
                pass
        response = Response({'detail': 'Logged out.'}, status=status.HTTP_200_OK)
        _clear_refresh_cookie(response)
        return response


class RegisterView(generics.CreateAPIView):
    """Public self-service signup for customers (ticket submitters)."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]


class VerifyOTPView(generics.GenericAPIView):
    """POST /api/verify-otp/ — confirms the emailed code and unlocks sign-in."""
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'detail': 'Email verified successfully.'}, status=status.HTTP_200_OK)


class ResendOTPView(generics.GenericAPIView):
    """POST /api/resend-otp/ — issues a fresh code, subject to a cooldown."""
    serializer_class = ResendOTPSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        profile = serializer.validated_data['profile']
        code = profile.generate_otp()
        send_otp_email(user, code)
        return Response({'detail': 'Verification code resent.'}, status=status.HTTP_200_OK)


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        profile = getattr(self.request.user, 'profile', None)
        if profile and profile.is_staff_role:
            return queryset
        return queryset.filter(created_by=self.request.user)

    def get_throttles(self):
        if self.action == 'triage':
            return [TriageRetryThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer):
        ticket = serializer.save(created_by=self.request.user)
        # The staff queue lists DecisionLogs, so the row has to exist before
        # the agent runs — otherwise a slow or failing triage leaves this
        # ticket invisible to staff. Triage fills the row in from a thread.
        decision = DecisionLog.objects.create(
            ticket=ticket, agent_reasoning='', proposed_action='')
        triage_in_background(ticket.pk, decision.pk)

    def perform_destroy(self, instance):
        """Only a closed ticket can be deleted — by its owner or by staff,
        get_queryset above already limits which tickets each can reach."""
        if instance.status != 'closed':
            raise PermissionDenied('Only closed tickets can be deleted.')
        instance.delete()

    @action(detail=True, methods=['post'])
    def triage(self, request, pk=None):
        """
        POST /api/tickets/{id}/triage/
        Re-runs the agent over a ticket whose triage failed or never finished.
        The first run is kicked off automatically on create, so this is the
        retry path, not the normal one.
        """
        ticket = self.get_object()
        decision = ticket.decisions.order_by('-created_at').first()

        if decision is None:
            decision = DecisionLog.objects.create(
                ticket=ticket, agent_reasoning='', proposed_action='')
        elif decision.human_decision:
            return Response(
                {'success': False,
                 'error': 'This ticket has already been decided by a human.'},
                status=status.HTTP_400_BAD_REQUEST)

        try:
            result = apply_triage(ticket, decision)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'decision_log_id': decision.id,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': True,
            'ticket_id': ticket.id,
            'category': result['category'],
            'urgency': result['urgency'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning'],
            'action': result['action'],
            'drafted_response': result['drafted_response'],
            'escalation_reason': result['escalation_reason'],
            'sources_cited': result['sources_cited'],
            'kb_articles_found': result['kb_articles_found'],
            'decision_log_id': decision.id,
            'status': ticket.status
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        """
        GET  /api/tickets/{id}/messages/ — the follow-up thread.
        POST /api/tickets/{id}/messages/ — add a follow-up message.
        Visibility matches the ticket itself: its owner, or any staff account.
        """
        ticket = self.get_object()

        if request.method == 'POST':
            profile = getattr(request.user, 'profile', None)
            is_staff_sender = bool(profile and profile.is_staff_role)

            if not is_staff_sender and self._consecutive_customer_messages(ticket) >= 3:
                return Response(
                    {'detail': 'Please wait for a staff reply before sending more follow-ups.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS)

            serializer = TicketMessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            message = TicketMessage.objects.create(
                ticket=ticket, sender=request.user,
                body=serializer.validated_data['body'])

            # A follow-up hands the ticket back to the other side: a customer
            # reply reopens it into the staff queue, a staff reply resolves
            # it again.
            if is_staff_sender and ticket.status == 'in_review':
                ticket.status = 'approved'
                ticket.save(update_fields=['status'])
            elif not is_staff_sender and ticket.status == 'approved':
                ticket.status = 'in_review'
                ticket.save(update_fields=['status'])

            return Response(
                TicketMessageSerializer(message).data, status=status.HTTP_201_CREATED)

        return Response(
            TicketMessageSerializer(ticket.messages.all(), many=True).data)

    @staticmethod
    def _consecutive_customer_messages(ticket):
        """How many customer messages in a row sit at the end of the thread,
        with no staff reply since. Caps follow-up spam before staff responds."""
        count = 0
        for message in ticket.messages.select_related('sender__profile').order_by('-created_at'):
            sender_profile = getattr(message.sender, 'profile', None)
            if sender_profile and sender_profile.is_staff_role:
                break
            count += 1
        return count

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        POST /api/tickets/{id}/close/
        Lets the customer who submitted the ticket mark it closed. Staff
        don't get this button — they use approve/reject on the decision.
        """
        ticket = self.get_object()
        if ticket.created_by_id != request.user.id:
            return Response(
                {'detail': 'Only the ticket owner can close it.'},
                status=status.HTTP_403_FORBIDDEN)
        if ticket.status == 'closed':
            return Response(
                {'detail': 'Ticket is already closed.'},
                status=status.HTTP_400_BAD_REQUEST)

        ticket.status = 'closed'
        ticket.save(update_fields=['status'])
        return Response(TicketSerializer(ticket).data)


class DecisionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DecisionLog.objects.select_related('ticket').all()
    serializer_class = DecisionLogSerializer
    permission_classes = [IsSupportStaff]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param == 'pending':
            # Never decided, or reopened by a customer follow-up after being
            # decided — both need staff attention.
            queryset = queryset.filter(
                Q(human_decision__isnull=True) | Q(ticket__status='in_review'))
        return queryset

    @action(detail=True, methods=['post'])
    def decide(self, request, pk=None):
        """
        POST /api/decisions/{id}/decide/
        Body: {"decision": "approved" | "rejected" | "edited", "edited_action"?: string}
        Records the human decision and updates the linked ticket's status.
        """
        decision_log = self.get_object()

        serializer = DecisionLogDecideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data['decision']

        decision_log.human_decision = decision
        if decision == 'edited':
            decision_log.edited_action = serializer.validated_data['edited_action']
        decision_log.decided_at = timezone.now()

        ticket = decision_log.ticket
        ticket.status = 'rejected' if decision == 'rejected' else 'approved'

        with transaction.atomic():
            decision_log.save()
            ticket.save()

        return Response(
            DecisionLogSerializer(decision_log).data,
            status=status.HTTP_200_OK
        )
