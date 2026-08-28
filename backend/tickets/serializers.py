import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.state import token_backend
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Ticket, DecisionLog, TicketMessage, UserProfile, TokenFamily
from .otp import send_otp_email


class TicketSerializer(serializers.ModelSerializer):
    resolution = serializers.SerializerMethodField()
    created_by_username = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'body', 'category', 'urgency', 'status',
                  'created_at', 'updated_at', 'resolution', 'created_by_username']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else None

    def get_resolution(self, obj):
        """The customer-facing reply, once staff has approved or edited one.
        None for a rejected decision — nothing was sent to the customer."""
        decision = obj.decisions.filter(
            human_decision__in=['approved', 'edited']).order_by('-decided_at').first()
        if not decision:
            return None
        return {
            'reply': decision.edited_action or decision.proposed_action,
            'sources': decision.sources_used,
            'decided_at': decision.decided_at,
        }


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    sender_role = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessage
        fields = ['id', 'sender_username', 'sender_role', 'body', 'created_at']
        read_only_fields = ['id', 'sender_username', 'sender_role', 'created_at']

    def get_sender_role(self, obj):
        profile = getattr(obj.sender, 'profile', None)
        return profile.role if profile else 'customer'


class DecisionLogSerializer(serializers.ModelSerializer):
    ticket = TicketSerializer(read_only=True)

    class Meta:
        model = DecisionLog
        fields = ['id', 'ticket', 'agent_reasoning', 'proposed_action',
                  'human_decision', 'sources_used', 'edited_action',
                  'triage_error', 'decided_at', 'created_at']
        read_only_fields = fields


class DecisionLogDecideSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=['approved', 'rejected', 'edited'])
    edited_action = serializers.CharField(
        required=False, allow_blank=False)

    def validate(self, data):
        if data['decision'] == 'edited' and not data.get('edited_action'):
            raise serializers.ValidationError(
                {'edited_action': 'Required when decision is "edited".'})
        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds the user's role to the JWT so the frontend can gate on it, and
    blocks sign-in for accounts that haven't confirmed their email yet."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        profile = getattr(user, 'profile', None)
        token['role'] = profile.role if profile else 'customer'
        # Starts a fresh reuse-detection family for this login session; each
        # refresh rotation carries the same family_id forward (see
        # CookieTokenRefreshSerializer below).
        outstanding = OutstandingToken.objects.get(jti=token['jti'])
        TokenFamily.objects.create(outstanding_token=outstanding, family_id=uuid.uuid4())
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        profile = getattr(self.user, 'profile', None)
        if profile and not profile.email_verified:
            raise serializers.ValidationError({
                'detail': 'Please verify your email before signing in.',
                'code': 'email_not_verified',
            })
        return data


class RegisterSerializer(serializers.ModelSerializer):
    """
    Public self-service signup — always creates a 'customer' account.
    Staff (agent/admin) accounts are provisioned via Django admin, never
    through this endpoint, so role is not accepted as input here.

    The account is created immediately but can't sign in until the emailed
    OTP is confirmed via /api/verify-otp/.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        profile = user.profile
        profile.role = 'customer'
        profile.email_verified = False
        profile.save(update_fields=['role', 'email_verified'])
        code = profile.generate_otp()
        send_otp_email(user, code)
        return user


class VerifyOTPSerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate(self, data):
        try:
            user = User.objects.get(username=data['username'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'username': 'No such account.'})

        profile = getattr(user, 'profile', None)
        if not profile:
            raise serializers.ValidationError({'username': 'No such account.'})
        if profile.email_verified:
            raise serializers.ValidationError({'detail': 'Email is already verified.'})
        if not profile.verify_otp(data['otp']):
            raise serializers.ValidationError({'otp': 'That code is invalid or has expired.'})

        data['user'] = user
        return data


class ResendOTPSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate(self, data):
        try:
            user = User.objects.get(username=data['username'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'username': 'No such account.'})

        profile = getattr(user, 'profile', None)
        if not profile:
            raise serializers.ValidationError({'username': 'No such account.'})
        if profile.email_verified:
            raise serializers.ValidationError({'detail': 'Email is already verified.'})

        remaining = profile.otp_cooldown_remaining()
        if remaining:
            raise serializers.ValidationError({
                'detail': f'Please wait {remaining}s before requesting another code.',
            })

        data['user'] = user
        data['profile'] = profile
        return data


class CookieTokenRefreshSerializer(serializers.Serializer):
    """
    Reads the refresh token from the httpOnly cookie (via context['request'])
    instead of the request body, and adds reuse-family revocation on top of
    SimpleJWT's built-in rotate/blacklist: if the incoming token's jti is
    already blacklisted — meaning it was already rotated once — every
    OutstandingToken sharing its login family is blacklisted too, since we
    can no longer tell the legitimate holder from whoever replayed it.
    """

    def validate(self, attrs):
        raw_token = self.context['request'].COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if not raw_token:
            raise InvalidToken('Refresh token missing.')

        old_jti = self._peek_jti(raw_token)

        try:
            refresh = RefreshToken(raw_token)
        except TokenError as e:
            if old_jti and BlacklistedToken.objects.filter(token__jti=old_jti).exists():
                self._revoke_family(old_jti)
            raise InvalidToken('Refresh token is invalid, expired, or was already used.') from e

        user_id = refresh.payload.get(jwt_settings.USER_ID_CLAIM)
        try:
            user = get_user_model().objects.get(**{jwt_settings.USER_ID_FIELD: user_id})
        except get_user_model().DoesNotExist:
            raise InvalidToken('No active account found for the given token.')
        if not jwt_settings.USER_AUTHENTICATION_RULE(user):
            raise InvalidToken('No active account found for the given token.')

        data = {'access': str(refresh.access_token)}

        if jwt_settings.ROTATE_REFRESH_TOKENS:
            if jwt_settings.BLACKLIST_AFTER_ROTATION:
                refresh.blacklist()
            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            refresh.outstand()
            data['refresh'] = str(refresh)
            self._carry_family(old_jti, refresh['jti'])

        return data

    @staticmethod
    def _peek_jti(raw_token):
        """Signature/exp-verified decode, used only to read jti — safe to
        trust even when the full Token() construction below is about to
        reject the token as blacklisted."""
        try:
            return token_backend.decode(raw_token, verify=True).get('jti')
        except Exception:
            return None

    @staticmethod
    def _carry_family(old_jti, new_jti):
        if not old_jti:
            return
        try:
            family_id = TokenFamily.objects.get(outstanding_token__jti=old_jti).family_id
        except TokenFamily.DoesNotExist:
            family_id = uuid.uuid4()
        new_outstanding = OutstandingToken.objects.get(jti=new_jti)
        TokenFamily.objects.create(outstanding_token=new_outstanding, family_id=family_id)

    @staticmethod
    def _revoke_family(compromised_jti):
        try:
            family_id = TokenFamily.objects.get(outstanding_token__jti=compromised_jti).family_id
        except TokenFamily.DoesNotExist:
            return
        family_tokens = OutstandingToken.objects.filter(family__family_id=family_id)
        for outstanding in family_tokens:
            BlacklistedToken.objects.get_or_create(token=outstanding)
