from django.db import models
from django.contrib.auth.models import User


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
    Each user has exactly one profile with either 'agent' or 'admin' role.
    """
    ROLE_CHOICES = [
        ('agent', 'Agent'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default='agent')
    created_at = models.DateTimeField(auto_now_add=True)

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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Decision for Ticket #{self.ticket.id}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Decision Log'
        verbose_name_plural = 'Decision Logs'
