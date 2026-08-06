from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Ticket, DecisionLog
from .serializers import TicketSerializer, DecisionLogSerializer, DecisionLogDecideSerializer
from .agent import categorize_ticket


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [AllowAny]  # remove this after login is made

    @action(detail=True, methods=['post'])
    def triage(self, request, pk=None):
        """
        POST /api/tickets/{id}/triage/
        Triggers AI agent to categorize the ticket.
        """
        ticket = self.get_object()

        try:
            # Call the agent
            result = categorize_ticket(ticket)

            # Update ticket with agent's categorization
            ticket.category = result['category']
            ticket.urgency = result['urgency']
            ticket.status = 'in_review'
            ticket.save()

            # Create decision log

            decision_log = DecisionLog.objects.create(
                ticket=ticket,
                agent_reasoning=result['reasoning'],
                proposed_action=result['drafted_response'] or result['escalation_reason'],
                sources_used=result['sources_cited']
            )

            # Return success response
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
                'decision_log_id': decision_log.id,
                'status': ticket.status
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DecisionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DecisionLog.objects.select_related('ticket').all()
    serializer_class = DecisionLogSerializer
    permission_classes = [AllowAny]  # remove this after login is made

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param == 'pending':
            queryset = queryset.filter(human_decision__isnull=True)
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
        decision_log.save()

        ticket = decision_log.ticket
        ticket.status = 'rejected' if decision == 'rejected' else 'approved'
        ticket.save()

        return Response(
            DecisionLogSerializer(decision_log).data,
            status=status.HTTP_200_OK
        )
