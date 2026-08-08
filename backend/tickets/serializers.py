from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Ticket, DecisionLog, UserProfile
from .otp import send_otp_email


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'body', 'category',
                  'urgency', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DecisionLogSerializer(serializers.ModelSerializer):
    ticket = TicketSerializer(read_only=True)

    class Meta:
        model = DecisionLog
        fields = ['id', 'ticket', 'agent_reasoning', 'proposed_action',
                  'human_decision', 'sources_used', 'edited_action',
                  'decided_at', 'created_at']
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
