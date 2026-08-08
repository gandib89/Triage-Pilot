from django.core.management.base import BaseCommand
from tickets.models import Ticket, DecisionLog
from tickets.agent import categorize_ticket


class Command(BaseCommand):
    help = 'Seeds the database with sample support tickets'

    def handle(self, *args, **kwargs):
        tickets_data = [
            {
                'subject': 'Cannot reset password',
                'body': 'I tried to reset my password but the email never arrived. I checked spam folder too. My email is john@example.com. Please help!',
            },
            {
                'subject': 'Billing - charged twice this month',
                'body': 'I noticed I was charged $29.99 twice on my credit card statement. My account ID is 12345. Can you refund the duplicate charge?',
            },
            {
                'subject': 'Account locked after failed login',
                'body': 'My account got locked after I mistyped my password 3 times. Username: sarah_m. How can I unlock it?',
            },
            {
                'subject': 'How do I export my data?',
                'body': 'I want to download all my data from your platform. Is there an export feature? Where can I find it?',
            },
            {
                'subject': 'Premium feature not working',
                'body': 'I upgraded to premium but the advanced analytics feature is still showing as locked. I already paid $49/month.',
            },
            {
                'subject': 'Delete my account',
                'body': 'I want to permanently delete my account and all associated data. How do I proceed?',
            },
            {
                'subject': 'API rate limit too low',
                'body': 'Our application needs more than 1000 API calls per hour. Current limit is blocking our service. Can we upgrade?',
            },
            {
                'subject': 'Refund request - unused subscription',
                'body': 'I signed up last week but never used the service. Can I get a refund for this month? Invoice #INV-8392',
            },
            {
                'subject': 'Two-factor authentication not sending codes',
                'body': 'Trying to log in but 2FA code never arrives on my phone. Number ending in 4567. Urgent!',
            },
            {
                'subject': 'How to integrate with Slack?',
                'body': 'We want to connect your platform with our Slack workspace. Is there documentation for this integration?',
            },
            {
                'subject': 'Account shows wrong billing address',
                'body': 'My billing address shows an old address from 2 years ago. How do I update it? Account email: mike@company.com',
            },
            {
                'subject': 'Can I transfer account to another user?',
                'body': 'I am leaving the company. How can I transfer account ownership to my replacement sarah@company.com?',
            },
            {
                'subject': 'Data breach concern',
                'body': 'I received a suspicious email claiming to be from your company asking for my password. Is this legitimate?',
            },
            {
                'subject': 'Enterprise plan pricing',
                'body': 'We have 500 employees and need enterprise features. What is the pricing for enterprise plan? Do you offer volume discounts?',
            },
            {
                'subject': 'App crashes on startup',
                'body': 'Mobile app crashes immediately after I open it. iPhone 14, iOS 17.2. Tried reinstalling but same issue.',
            },
        ]

        Ticket.objects.all().delete()  # Clear existing tickets

        for data in tickets_data:
            ticket = Ticket.objects.create(**data)

            try:
                result = categorize_ticket(ticket)
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f'  Triage failed for "{ticket.subject}": {e}'))
                continue

            ticket.category = result['category']
            ticket.urgency = result['urgency']
            ticket.status = 'in_review'
            ticket.save()

            DecisionLog.objects.create(
                ticket=ticket,
                agent_reasoning=result['reasoning'],
                proposed_action=result['drafted_response'] or result['escalation_reason'],
                sources_used=result['sources_cited']
            )

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {len(tickets_data)} sample tickets'))
