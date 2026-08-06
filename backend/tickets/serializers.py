from rest_framework import serializers
from .models import Ticket, DecisionLog


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'body', 'category',
                  'urgency', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DecisionLogSerializer(serializers.ModelSerializer):
    ticket = TicketSerializer(read_only=True)

    class Meta:
        model = DecisionLog
        fields = ['id', 'ticket', 'agent_reasoning', 'proposed_action',
                  'human_decision', 'sources_used', 'edited_action',
                  'decided_at', 'created_at']
        read_only_fields = fields


class DecisionLogDecideSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=['approved', 'rejected', 'edited'])
    edited_action = serializers.CharField(
        required=False, allow_blank=False)

    def validate(self, data):
        if data['decision'] == 'edited' and not data.get('edited_action'):
            raise serializers.ValidationError(
                {'edited_action': 'Required when decision is "edited".'})
        return data
