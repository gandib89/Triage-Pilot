from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Ticket, DecisionLog
from .serializers import TicketSerializer, DecisionLogSerializer
from .agent import categorize_ticket


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    @action(detail=True, methods=["post"], url_path="triage")
    def triage(self, request, pk=None):
        ticket = self.get_object()

        result = categorize_ticket(ticket)

        ticket.category = result["category"]
        ticket.urgency = result["urgency"]
        ticket.status = "in_review"
        ticket.save()

        DecisionLog.objects.create(
            ticket=ticket,
            agent_reasoning=result["reasoning"],
            proposed_action=f"Categorized as {result['category']} with {result['urgency']} urgency",
            sources_used=[],
        )

        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="decisions")
    def decisions(self, request, pk=None):
        ticket = self.get_object()
        logs = ticket.decisions.all()
        serializer = DecisionLogSerializer(logs, many=True)
        return Response(serializer.data)
