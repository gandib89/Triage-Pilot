import random
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

OTP_LIFETIME = timedelta(minutes=10)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('billing', 'Billing'),
        ('account', 'Account'),
        ('general', 'General'),
    ]

    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='tickets',
        null=True, blank=True,
        help_text="The customer who submitted this ticket.")
    subject = models.CharField(max_length=255)
    body = models.TextField()
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, null=True, blank=True)
    urgency = models.CharField(
        max_length=50, choices=URGENCY_CHOICES, null=True, blank=True)
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.subject) if self.subject else "Untitled Ticket"

    class Meta:
        ordering = ['-created_at']


class UserProfile(models.Model):
    """
    Extends the built-in User model with a role field.

    'customer' accounts are ticket submitters and self-register.
    'agent' and 'admin' accounts are support staff who take part in the
    human-in-the-loop triage queue; those are provisioned by an admin
    (via Django admin), not through self-service signup.
    """
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('agent', 'Agent'),
        ('admin', 'Admin'),
    ]
    STAFF_ROLES = ('agent', 'admin')

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)

    # Email verification, via a one-time code. Accounts created outside of
    # public self-signup (Django admin, shell) default to already-verified —
    # only the public /register/ flow needs the OTP round-trip.
    email_verified = models.BooleanField(default=True)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_last_sent_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_staff_role(self) -> bool:
        return self.role in self.STAFF_ROLES

    def otp_cooldown_remaining(self) -> int:
        if not self.otp_last_sent_at:
            return 0
        elapsed = timezone.now() - self.otp_last_sent_at
        remaining = OTP_RESEND_COOLDOWN - elapsed
        return max(0, int(remaining.total_seconds()))

    def generate_otp(self) -> str:
        code = f"{random.randint(0, 999999):06d}"
        now = timezone.now()
        self.otp_code = code
        self.otp_expires_at = now + OTP_LIFETIME
        self.otp_last_sent_at = now
        self.save(update_fields=['otp_code', 'otp_expires_at', 'otp_last_sent_at'])
        return code

    def verify_otp(self, code: str) -> bool:
        if not self.otp_code or not self.otp_expires_at:
            return False
        if timezone.now() > self.otp_expires_at:
            return False
        if self.otp_code != code:
            return False
        self.email_verified = True
        self.otp_code = None
        self.otp_expires_at = None
        self.save(update_fields=['email_verified', 'otp_code', 'otp_expires_at'])
        return True

    def __str__(self) -> str:
        return f"{self.user.username} - {self.role}"

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


class DecisionLog(models.Model):
    """
    Logs every decision made by the AI agent for audit trail.
    """
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name='decisions')
    agent_reasoning = models.TextField(
        help_text="Why the agent made this decision")
    proposed_action = models.TextField(
        help_text="What the agent suggests doing")
    human_decision = models.CharField(
        max_length=50,
        choices=[
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('edited', 'Edited'),
        ],
        null=True,
        blank=True,
        help_text="What the human decided"
    )
    sources_used = models.JSONField(
        default=list,
        blank=True,
        help_text="KB articles or sources the agent cited"
    )
    edited_action = models.TextField(
        null=True,
        blank=True,
        help_text="Human-edited version of the proposed action, if edited"
    )
    decided_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the human made a decision on this item"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Decision for Ticket #{self.ticket.id}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Decision Log'
        verbose_name_plural = 'Decision Logs'
        
