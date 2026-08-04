"""
AI Agent service for ticket categorization.
Uses local LLM via Ollama to analyze support tickets.
"""
from typing import Dict, Any
import json
import ollama


def build_prompt(ticket) -> str:
    """
    Build a structured prompt for the LLM.
    """
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


def call_ollama(prompt: str, model: str = "llama3.2") -> str:
    """
    Call Ollama API with the prompt.
    """
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': 0.3,  # Lower = more consistent
                'num_predict': 200,  # Max tokens to generate
            }
        )

        return response['message']['content']

    except Exception as e:
        raise Exception(f"Ollama API error: {str(e)}")


def parse_response(response: str) -> Dict[str, Any]:
    """
    Parse JSON response from LLM.
    Handles cases where LLM includes markdown or extra text.
    """
    # Try to find JSON in the response
    response = response.strip()

    # Remove markdown code blocks if present
    if response.startswith('```'):
        # Extract content between ``` markers
        lines = response.split('\n')
        response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
        response = response.replace('```json', '').replace('```', '').strip()

    try:
        data = json.loads(response)

        # Validate required fields
        required_fields = ['category', 'urgency', 'confidence', 'reasoning']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Validate category
        valid_categories = ['technical', 'billing', 'account', 'general']
        if data['category'] not in valid_categories:
            data['category'] = 'general'  # Default fallback

        # Validate urgency
        valid_urgencies = ['low', 'medium', 'high', 'critical']
        if data['urgency'] not in valid_urgencies:
            data['urgency'] = 'medium'  # Default fallback

        # Validate confidence (0-100)
        data['confidence'] = max(0, min(100, int(data['confidence'])))

        return data

    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse JSON response: {str(e)}\nResponse: {response}")


def categorize_ticket(ticket) -> Dict[str, Any]:
    """
    Main function: Categorize a ticket using the AI agent.

    Returns:
        {
            'category': str,
            'urgency': str,
            'confidence': int,
            'reasoning': str
        }
    """
    # Build prompt
    prompt = build_prompt(ticket)

    # Call LLM
    response = call_ollama(prompt)

    # Parse response
    result = parse_response(response)

    return result
