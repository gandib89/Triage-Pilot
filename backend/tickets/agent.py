"""
AI Agent service for ticket categorization.
Uses local LLM via Ollama to analyze support tickets.
"""
import json
import ollama
from typing import Dict, Any
from .knowledge_base import search_knowledge_base


def build_prompt(ticket) -> str:
    """Build a structured prompt for the LLM."""
    prompt = f"""You are a support ticket categorization assistant. Analyze the support ticket and respond with ONLY a JSON object.

Ticket Subject: {ticket.subject}
Ticket Body: {ticket.body}

Respond with this exact JSON format:
{{
    "category": "technical" | "billing" | "account" | "general",
    "urgency": "low" | "medium" | "high" | "critical",
    "confidence": 0-100,
    "reasoning": "brief explanation"
}}

Category Guidelines:
- technical: bugs, crashes, API issues, 2FA problems, system errors, integrations
- billing: payments, refunds, invoices, pricing, subscription changes
- account: login, ownership transfer, account settings, deletion, permissions
- general: how-to questions, documentation, feature requests, general inquiries

Urgency Guidelines:
- critical: system down, data breach, security incident, payment processing failure
- high: account locked, service broken, urgent business blocker (customer uses words like "urgent", "ASAP")
- medium: non-urgent bugs, billing questions, feature requests
- low: how-to questions, documentation requests, general inquiries

Confidence Guidelines:
- 80-100: Clear category and urgency, unambiguous ticket
- 60-79: Probable category, minor ambiguity
- 40-59: Uncertain, could fit multiple categories
- 0-39: Very unclear or insufficient information

IMPORTANT: Respond with ONLY valid JSON, no markdown code blocks, no explanations."""

    return prompt


def call_ollama(prompt: str, model: str = "llama3.2:latest", timeout: int = 60) -> str:
    """Call Ollama API with the prompt."""
    try:
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            options={
                'temperature': 0.3,
                'num_predict': 300,
            }
        )
        return response['message']['content']

    except Exception as e:
        raise Exception(f"Ollama API error: {str(e)}")


def parse_response(response: str) -> Dict[str, Any]:
    """Parse JSON response from LLM."""
    response = response.strip()

    if response.startswith('```'):
        lines = response.split('\n')
        response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
        response = response.replace('```json', '').replace('```', '').strip()

    # Try to fix incomplete JSON by adding closing brace
    if not response.endswith('}'):
        response = response + '}'

    try:
        data = json.loads(response)

        required_fields = ['category', 'urgency', 'confidence', 'reasoning']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        valid_categories = ['technical', 'billing', 'account', 'general']
        if data['category'] not in valid_categories:
            data['category'] = 'general'

        valid_urgencies = ['low', 'medium', 'high', 'critical']
        if data['urgency'] not in valid_urgencies:
            data['urgency'] = 'medium'

        data['confidence'] = max(0, min(100, int(data['confidence'])))

        return data

    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse JSON response: {str(e)}\nResponse: {response}")


def build_decision_prompt(ticket, category: str, urgency: str, kb_articles: list) -> str:
    """Build a prompt for drafting a response using KB articles."""
    kb_context = ""
    if kb_articles:
        kb_context = "\n\nRelevant Knowledge Base Articles:\n"
        for i, article in enumerate(kb_articles, 1):
            kb_context += f"\n[{article['id']}] {article['title']} (relevance: {article['relevance_score']}):\n{article['content']}\n"
        example_id = kb_articles[0]['id']
    else:
        kb_context = "\n\nNo relevant KB articles found. This ticket requires human review."
        example_id = "KB001"

    prompt = f"""You are a support agent assistant. Based on the ticket and available knowledge base articles, decide the best action.

Ticket Subject: {ticket.subject}
Ticket Body: {ticket.body}
Category: {category}
Urgency: {urgency}
{kb_context}

Respond with ONLY this JSON format:
{{
    "action": "reply" | "escalate",
    "drafted_response": "customer-facing reply text OR empty string",
    "escalation_reason": "reason for escalation OR empty string",
    "sources_cited": ["{example_id}"]
}}

Decision Rules:
1. Use "reply" ONLY if:
   - KB articles clearly address the issue
   - You can provide specific steps or information
   - The issue is straightforward (password reset, billing info, how-to)

2. Use "escalate" if:
   - No KB articles match the issue
   - Issue is critical or complex (security, data loss, system outage)
   - Customer situation requires human judgment
   - KB articles are vaguely related but don't solve the problem

Drafted Response Guidelines (if action is "reply"):
- Be professional and empathetic
- Cite the exact article ID shown in brackets above, e.g. "According to [{example_id}]..." — never invent an ID that isn't listed above
- Provide clear, actionable steps
- Keep under 150 words
- Include contact info if needed: support@company.com

IMPORTANT: Only cite KB articles that are directly relevant (high relevance score). Don't cite articles just because they're listed.

Respond with ONLY valid JSON, no markdown blocks."""

    return prompt


def parse_decision_response(response: str) -> dict:
    """Parse the decision JSON from LLM."""
    response = response.strip()

    if response.startswith('```'):
        lines = response.split('\n')
        response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
        response = response.replace('```json', '').replace('```', '').strip()

    # Try to fix incomplete JSON by adding closing brace
    if not response.endswith('}'):
        response = response + '}'

    try:
        data = json.loads(response)

        if data.get('action') not in ['reply', 'escalate']:
            data['action'] = 'escalate'

        data.setdefault('drafted_response', '')
        data.setdefault('escalation_reason', '')
        data.setdefault('sources_cited', [])

        return data

    except json.JSONDecodeError as e:
        return {
            'action': 'escalate',
            'drafted_response': '',
            'escalation_reason': f'Could not parse agent response: {str(e)}',
            'sources_cited': []
        }


def categorize_ticket(ticket) -> dict:
    """
    Main function: Categorize a ticket and draft a response using KB.
    """
    # Step 1: Categorize
    prompt = build_prompt(ticket)
    response = call_ollama(prompt)
    categorization = parse_response(response)

    # Step 2: Check confidence threshold
    # If confidence is too low, escalate immediately
    if categorization['confidence'] < 50:
        return {
            'category': categorization['category'],
            'urgency': 'medium',  # Default to medium for low-confidence cases
            'confidence': categorization['confidence'],
            'reasoning': categorization['reasoning'],
            'action': 'escalate',
            'drafted_response': '',
            'escalation_reason': f"Low confidence ({categorization['confidence']}%) in categorization. Requires human review.",
            'sources_cited': [],
            'kb_articles_found': 0,
        }

    # Step 3: Search KB
    search_query = f"{ticket.subject} {ticket.body}"
    kb_articles = search_knowledge_base(
        query=search_query,
        category=categorization['category'],
        max_results=3
    )

    # Step 4: Draft response
    decision_prompt = build_decision_prompt(
        ticket=ticket,
        category=categorization['category'],
        urgency=categorization['urgency'],
        kb_articles=kb_articles
    )
    decision_response = call_ollama(decision_prompt)
    decision = parse_decision_response(decision_response)

    # Step 5: Return combined result
    return {
        'category': categorization['category'],
        'urgency': categorization['urgency'],
        'confidence': categorization['confidence'],
        'reasoning': categorization['reasoning'],
        'action': decision['action'],
        'drafted_response': decision['drafted_response'],
        'escalation_reason': decision['escalation_reason'],
        'sources_cited': decision['sources_cited'],
        'kb_articles_found': len(kb_articles),
    }
