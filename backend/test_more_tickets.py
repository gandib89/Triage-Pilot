# Run this via: python manage.py shell < test_more_tickets.py

from tickets.models import Ticket
from tickets.agent import categorize_ticket

print("\nTesting tickets #6-10 through the pipeline...")
print("=" * 80)

tickets = Ticket.objects.all()[5:10]

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
