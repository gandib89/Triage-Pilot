"""
Test script for Day 4: Run multiple tickets through the triage pipeline.
Run from the backend directory: python test_triage_pipeline.py
"""
from tickets.agent import categorize_ticket
from tickets.models import Ticket
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()


def test_pipeline(start=0, count=5):
    """Run test tickets through the pipeline."""

    # Get tickets
    tickets = Ticket.objects.all()[start:start + count]

    if not tickets:
        print("No tickets found. Run: python manage.py seed_tickets")
        return

    print(f"Testing tickets #{start + 1} to #{start + len(tickets)} through the pipeline...\n")
    print("=" * 80)

    for ticket in tickets:
        print(f"\n📧 TICKET #{ticket.id}: {ticket.subject}")
        print(f"Body: {ticket.body[:100]}...")
        print("-" * 80)

        try:
            result = categorize_ticket(ticket)

            print(f"✅ Category: {result['category']}")
            print(f"✅ Urgency: {result['urgency']}")
            print(f"✅ Confidence: {result['confidence']}%")
            print(f"✅ Reasoning: {result['reasoning']}")
            print(f"✅ Action: {result['action']}")
            print(f"✅ KB Articles Found: {result['kb_articles_found']}")

            if result['action'] == 'reply':
                print(f"\n💬 Drafted Response:\n{result['drafted_response']}")
                if result['sources_cited']:
                    print(f"📚 Sources: {', '.join(result['sources_cited'])}")
            else:
                print(f"\n⚠️  Escalation Reason: {result['escalation_reason']}")

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")

        print("=" * 80)


if __name__ == '__main__':
    # Allow passing start index: python test_triage_pipeline.py 5
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    test_pipeline(start, count)
