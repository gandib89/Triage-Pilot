from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Ticket, DecisionLog
from .serializers import TicketSerializer
from .agent import categorize_ticket


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [AllowAny]  # remove this after login is made

    @action(detail=True, methods=['post'])
    def triage(self, request, pk=None):
        """
        POST /api/tickets/{id}/triage/
        Triggers AI agent to categorize the ticket.
        """
        ticket = self.get_object()

        try:
            # Call the agent
            result = categorize_ticket(ticket)

            # Update ticket with agent's categorization
            ticket.category = result['category']
            ticket.urgency = result['urgency']
            ticket.status = 'in_review'
            ticket.save()

            # Create decision log

            decision_log = DecisionLog.objects.create(
                ticket=ticket,
                agent_reasoning=result['reasoning'],
                proposed_action=result['drafted_response'] or result['escalation_reason'],
                sources_used=', '.join(
                    result['sources_cited']) if result['sources_cited'] else 'None'
            )

            # Return success response
            return Response({
                'success': True,
                'ticket_id': ticket.id,
                'category': result['category'],
                'urgency': result['urgency'],
                'confidence': result['confidence'],
                'reasoning': result['reasoning'],
                'action': result['action'],
                'drafted_response': result['drafted_response'],
                'escalation_reason': result['escalation_reason'],
                'sources_cited': result['sources_cited'],
                'kb_articles_found': result['kb_articles_found'],
                'decision_log_id': decision_log.id,
                'status': ticket.status
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
