from django.core.management.base import BaseCommand
from tickets.models import Ticket
from tickets.agent import categorize_ticket


class Command(BaseCommand):
    help = 'Test edge cases in the triage pipeline'

    def handle(self, *args, **kwargs):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("TESTING EDGE CASES")
        self.stdout.write("=" * 80)

        # Test for critical urgency
        self.stdout.write("\n1. Testing CRITICAL urgency ticket...")
        self.stdout.write("-" * 80)
        critical_tickets = Ticket.objects.filter(urgency='critical')
        if critical_tickets.exists():
            ticket = critical_tickets.first()
            self.test_ticket(ticket, "Critical Urgency")
        else:
            self.stdout.write(self.style.WARNING("No critical tickets found in database"))

        # Test for high urgency
        self.stdout.write("\n2. Testing HIGH urgency ticket...")
        self.stdout.write("-" * 80)
        high_tickets = Ticket.objects.filter(urgency='high')
        if high_tickets.exists():
            ticket = high_tickets.first()
            self.test_ticket(ticket, "High Urgency")
        else:
            self.stdout.write(self.style.WARNING("No high urgency tickets found"))

        # Test tickets with no category match (ambiguous)
        self.stdout.write("\n3. Testing potentially ambiguous ticket...")
        self.stdout.write("-" * 80)
        general_tickets = Ticket.objects.filter(category='general') | Ticket.objects.filter(category__isnull=True)
        if general_tickets.exists():
            ticket = general_tickets.first()
            self.test_ticket(ticket, "Ambiguous/General")
        else:
            self.stdout.write(self.style.WARNING("No general/ambiguous tickets found"))

        # Test a ticket that might lead to escalation
        self.stdout.write("\n4. Looking for escalation cases...")
        self.stdout.write("-" * 80)
        from tickets.models import DecisionLog
        escalated = DecisionLog.objects.filter(proposed_action__icontains='escalat')
        if escalated.exists():
            decision = escalated.first()
            self.stdout.write(f"Found escalation in Ticket #{decision.ticket.id}")
            self.stdout.write(f"Subject: {decision.ticket.subject}")
            self.stdout.write(f"Escalation reason: {decision.proposed_action}")
        else:
            self.stdout.write(self.style.WARNING("No escalation cases found in decision logs"))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("EDGE CASE TESTING COMPLETE")
        self.stdout.write("=" * 80)

    def test_ticket(self, ticket, label):
        self.stdout.write(f"\n[{label}] TICKET #{ticket.id}: {ticket.subject}")
        self.stdout.write(f"Body: {ticket.body[:100]}...")
        
        try:
            result = categorize_ticket(ticket)
            
            self.stdout.write(f"Category: {result['category']}")
            self.stdout.write(f"Urgency: {result['urgency']}")
            self.stdout.write(f"Confidence: {result['confidence']}%")
            self.stdout.write(f"Action: {result['action']}")
            self.stdout.write(f"KB Articles: {result['kb_articles_found']}")
            
            if result['action'] == 'escalate':
                self.stdout.write(self.style.WARNING(f"ESCALATED: {result['escalation_reason']}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"REPLY drafted with {len(result['sources_cited'])} sources"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ERROR: {str(e)}"))
