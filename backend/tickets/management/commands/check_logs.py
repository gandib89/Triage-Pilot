from django.core.management.base import BaseCommand
from tickets.models import DecisionLog, Ticket


class Command(BaseCommand):
    help = 'Check decision logs created during testing'

    def handle(self, *args, **kwargs):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("DECISION LOG AUDIT")
        self.stdout.write("=" * 80)

        logs = DecisionLog.objects.all().order_by('-created_at')[:10]
        
        if not logs:
            self.stdout.write(self.style.WARNING("No decision logs found!"))
            self.stdout.write("Run: curl -X POST http://localhost:8000/api/tickets/1/triage/")
            return

        self.stdout.write(f"\nShowing last {len(logs)} decision logs:\n")

        for i, log in enumerate(logs, 1):
            self.stdout.write(f"\n{i}. Log ID: {log.id} | Created: {log.created_at.strftime('%Y-%m-%d %H:%M')}")
            self.stdout.write(f"   Ticket: #{log.ticket.id} - {log.ticket.subject}")
            self.stdout.write(f"   Category: {log.ticket.category} | Urgency: {log.ticket.urgency}")
            self.stdout.write(f"   Reasoning: {log.agent_reasoning[:100]}...")
            self.stdout.write(f"   Action: {log.proposed_action[:80]}...")
            self.stdout.write(f"   Sources: {log.sources_used}")
            self.stdout.write(f"   Human Decision: {log.human_decision or 'Pending'}")
            self.stdout.write("-" * 80)

        self.stdout.write(f"\n✅ Total Decision Logs: {DecisionLog.objects.count()}")
        self.stdout.write(f"✅ Total Tickets: {Ticket.objects.count()}")
        self.stdout.write(f"✅ Tickets in Review: {Ticket.objects.filter(status='in_review').count()}")
        self.stdout.write(f"✅ Tickets Pending: {Ticket.objects.filter(status='pending').count()}")
        
        self.stdout.write("\n" + "=" * 80)
