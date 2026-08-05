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
    prompt = f"""You are a support ticket categorization assistant. Analyze the following support ticket and respond with ONLY a JSON object (no markdown, no explanation).

Ticket Subject: {ticket.subject}
Ticket Body: {ticket.body}

Categorize this ticket and respond with this exact JSON format:
{{
    "category": "technical" or "billing" or "account" or "general",
    "urgency": "low" or "medium" or "high" or "critical",
    "confidence": <number between 0-100>,
    "reasoning": "<brief explanation of your decision>"
}}

Rules:
- technical: password resets, bugs, API issues, technical problems
- billing: payments, refunds, invoices, pricing questions
- account: login issues, account settings, profile changes, ownership
- general: questions, how-to, feature requests, general inquiries

- critical: system down, data breach, payment failure
- high: account locked, service not working, urgent business need
- medium: feature requests, non-urgent bugs, billing questions
- low: general questions, how-to, documentation

Respond with ONLY the JSON, nothing else."""

    return prompt


def call_ollama(prompt: str, model: str = "llama3.2:3b") -> str:
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
            kb_context += f"\n[{article['id']}] {article['title']}:\n{article['content']}\n"
    else:
        kb_context = "\n\nNo relevant KB articles found."

    prompt = f"""You are a support agent assistant. Based on the ticket and knowledge base articles below, decide the best action.

Ticket Subject: {ticket.subject}
Ticket Body: {ticket.body}
Category: {category}
Urgency: {urgency}
{kb_context}

Decide the action and respond with ONLY this JSON format:
{{
    "action": "reply" or "escalate",
    "drafted_response": "<draft reply to customer if action is reply, empty string if escalate>",
    "escalation_reason": "<reason for escalation if action is escalate, empty string if reply>",
    "sources_cited": ["<list of KB article IDs used, e.g. KB001>"]
}}

Rules:
- Use "reply" if KB articles provide a clear solution
- Use "escalate" if no KB article helps OR issue is critical/complex
- drafted_response must be professional and cite KB sources
- Keep drafted_response under 150 words

Respond with ONLY the JSON, nothing else."""

    return prompt


def parse_decision_response(response: str) -> dict:
    """Parse the decision JSON from LLM."""
    response = response.strip()

    if response.startswith('```'):
        lines = response.split('\n')
        response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
        response = response.replace('```json', '').replace('```', '').strip()

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

    # Step 2: Search KB
    search_query = f"{ticket.subject} {ticket.body}"
    kb_articles = search_knowledge_base(
        query=search_query,
        category=categorization['category'],
        max_results=3
    )

    # Step 3: Draft response
    decision_prompt = build_decision_prompt(
        ticket=ticket,
        category=categorization['category'],
        urgency=categorization['urgency'],
        kb_articles=kb_articles
    )
    decision_response = call_ollama(decision_prompt)
    decision = parse_decision_response(decision_response)

    # Step 4: Return combined result
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
