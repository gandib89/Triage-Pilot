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
        ('closed', 'Closed'),
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


class DocumentChunk(models.Model):
    """
    A chunk of an ingested knowledge-base document, with its embedding.

    The embedding is stored as a JSON list of floats because the project is on
    SQLite for now. Vectors are written normalised, so cosine similarity is a
    dot product; when this table moves to PostgreSQL the column becomes a
    pgvector VectorField and the Python scan in tickets/rag.py becomes an
    ORDER BY on the vector distance operator.
    """
    document_name = models.CharField(
        max_length=255, db_index=True,
        help_text="Source file the chunk came from.")
    page = models.PositiveIntegerField(
        help_text="1-based page number in the source document.")
    section = models.CharField(
        max_length=255, blank=True, default='',
        help_text="Nearest heading above the chunk, if one was detected.")
    chunk_index = models.PositiveIntegerField(
        help_text="Position of the chunk within its document.")
    content = models.TextField()
    token_count = models.PositiveIntegerField(
        help_text="Estimated tokens in the chunk (~4 chars per token).")
    category = models.CharField(
        max_length=50, choices=Ticket.CATEGORY_CHOICES,
        null=True, blank=True, db_index=True,
        help_text="Optional category filter, matching ticket categories.")
    embedding = models.JSONField(
        help_text="Normalised embedding vector.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.document_name} #{self.chunk_index} (p. {self.page})"

    class Meta:
        ordering = ['document_name', 'chunk_index']
        unique_together = [('document_name', 'chunk_index')]
        verbose_name = 'Document Chunk'
        verbose_name_plural = 'Document Chunks'


class KnowledgeDocument(models.Model):
    """
    A PDF uploaded via Django admin to feed the RAG knowledge base. Saving it
    in admin extracts, chunks and embeds the file (tickets/rag.py) into
    DocumentChunk rows — that's what search_knowledge_base actually queries.
    """
    file = models.FileField(upload_to='kb_documents/')
    category = models.CharField(
        max_length=50, choices=Ticket.CATEGORY_CHOICES, null=True, blank=True,
        help_text="Optional category filter for retrieval.")
    chunk_count = models.PositiveIntegerField(default=0, editable=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.file.name.rsplit('/', 1)[-1]

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Knowledge Document'
        verbose_name_plural = 'Knowledge Documents'


class TicketMessage(models.Model):
    """
    Follow-up message on a ticket, after the initial AI-triaged decision.
    A plain back-and-forth thread between the customer and staff — it does
    not re-run the agent or create a new DecisionLog.
    """
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='ticket_messages')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Message on Ticket #{self.ticket_id} by {self.sender.username}"

    class Meta:
        ordering = ['created_at']


class UserProfile(models.Model):
    """
    Extends the built-in User model with a role field.

    'customer' accounts are ticket submitters and self-register.
    'staff' and 'admin' accounts are support staff who take part in the
    human-in-the-loop triage queue; those are provisioned by an admin
    (via Django admin), not through self-service signup.
    """
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    STAFF_ROLES = ('staff', 'admin')

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
        
