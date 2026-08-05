from django.core.management.base import BaseCommand
from tickets.models import Ticket
from tickets.agent import categorize_ticket


class Command(BaseCommand):
    help = 'Test first 5 tickets with tuned prompts'

    def handle(self, *args, **kwargs):
        self.stdout.write("\nTesting tickets #1-5 with TUNED prompts...")
        self.stdout.write("=" * 80)

        tickets = Ticket.objects.all()[:5]

        for ticket in tickets:
            self.stdout.write(f"\nTICKET #{ticket.id}: {ticket.subject}")
            self.stdout.write(f"Body: {ticket.body[:100]}...")
            self.stdout.write("-" * 80)

            try:
                result = categorize_ticket(ticket)

                self.stdout.write(f"Category: {result['category']}")
                self.stdout.write(f"Urgency: {result['urgency']}")
                self.stdout.write(f"Confidence: {result['confidence']}%")
                self.stdout.write(f"Reasoning: {result['reasoning']}")
                self.stdout.write(f"Action: {result['action']}")
                self.stdout.write(f"KB Articles Found: {result['kb_articles_found']}")

                if result['action'] == 'reply':
                    self.stdout.write(f"\nDrafted Response:\n{result['drafted_response']}")
                    if result['sources_cited']:
                        self.stdout.write(f"Sources: {', '.join(result['sources_cited'])}")
                else:
                    self.stdout.write(f"\nEscalation Reason: {result['escalation_reason']}")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"ERROR: {str(e)}"))

            self.stdout.write("=" * 80)
