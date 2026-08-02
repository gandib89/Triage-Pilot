from django.db import models


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
