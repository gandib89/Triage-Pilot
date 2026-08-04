from rest_framework import serializers
from .models import Ticket, DecisionLog


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'body', 'category',
                  'urgency', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DecisionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionLog
        fields = ['id', 'agent_reasoning', 'proposed_action',
                  'human_decision', 'sources_used', 'created_at']
        read_only_fields = fields
