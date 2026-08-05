from django.core.management.base import BaseCommand
from tickets.models import Ticket
from tickets.agent import categorize_ticket

# Create a very ambiguous ticket to test confidence threshold
ticket = Ticket(
    subject="Need help",
    body="Something is not working right."
)

print("\nTesting confidence threshold with ambiguous ticket...")
print("=" * 80)
print(f"Subject: {ticket.subject}")
print(f"Body: {ticket.body}")
print("-" * 80)

result = categorize_ticket(ticket)

print(f"Category: {result['category']}")
print(f"Urgency: {result['urgency']}")
print(f"Confidence: {result['confidence']}%")
print(f"Reasoning: {result['reasoning']}")
print(f"Action: {result['action']}")

if result['action'] == 'escalate':
    print(f"\n⚠️ ESCALATED: {result['escalation_reason']}")
else:
    print(f"\n✅ REPLY: {result['drafted_response'][:100]}...")

print("=" * 80)
