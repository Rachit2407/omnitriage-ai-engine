import os
from typing import Dict, Any, List
from core.rag_engine import RAGEngine
from core.guardrails import GuardrailAuditor

class SupportTriageAgent:
    """
    Main orchestration agent:
    1. Embeds and retrieves relevant documentation chunks.
    2. Synthesizes a technical response with exact citations.
    3. Runs an adversarial guardrail audit.
    4. Routes the ticket (AUTO_RESOLVE_DISPATCH vs. ESCALATE_HUMAN_TIER_2).
    """
    def __init__(self, rag: RAGEngine, auditor: GuardrailAuditor):
        self.rag = rag
        self.auditor = auditor
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = None
        if self.api_key and not self.api_key.startswith("your_"):
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except Exception:
                self.client = None

    def process_ticket(self, user_ticket: str) -> Dict[str, Any]:
        # Step 1: Context Retrieval via RAG
        chunks = self.rag.retrieve_context(user_ticket, top_k=2)
        context_str = "\n\n".join([f"Source ({c['source']}) - {c.get('title', '')}:\n{c['content']}" for c in chunks])

        # Step 2: Synthesis
        if self.client:
            system_prompt = (
                "You are an Elite Technical Support Engineer at a high-growth B2B developer platform. "
                "Resolve the customer's inquiry with extreme precision, citing exact documentation rules. "
                "Never invent policies or promise features not explicitly backed by the provided documentation. "
                "If the documentation does not permit an action (e.g. retrieving secret keys), politely explain "
                "the security policy and guide the user through the standard self-service procedure."
            )
            user_prompt = f"Official Knowledge Base Context:\n{context_str}\n\nCustomer Ticket:\n{user_ticket}"
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1
                )
                drafted_reply = response.choices[0].message.content
            except Exception as e:
                drafted_reply = self._generate_deterministic_reply(user_ticket, chunks)
        else:
            drafted_reply = self._generate_deterministic_reply(user_ticket, chunks)

        # Step 3: Adversarial Guardrail Audit
        verdict = self.auditor.audit_response(user_ticket, context_str, drafted_reply)

        # Step 4: Decision Routing
        if verdict.can_safely_send:
            action = "AUTO_RESOLVE_SENT"
            status = "RESOLVED"
            routed_to = "Customer Inbox (Automated SLA < 2s)"
        else:
            action = "ESCALATE_TO_HUMAN_TIER_2"
            status = "HUMAN_TRIAGE_REQUIRED"
            routed_to = "Senior Support Queue (Zendesk Priority Tag)"

        return {
            "ticket": user_ticket,
            "drafted_reply": drafted_reply,
            "verdict": verdict.model_dump(),
            "recommended_action": action,
            "status": status,
            "routed_to": routed_to,
            "citations": [c['source'] for c in chunks]
        }

    def _generate_deterministic_reply(self, ticket: str, chunks: List[Dict[str, Any]]) -> str:
        """Deterministic high-fidelity response generator for demo without API key."""
        t_low = ticket.lower()
        if "webhook" in t_low and ("retry" in t_low or "down" in t_low or "fail" in t_low):
            return (
                "Hello,\n\nOur system automatically retries failed webhook deliveries up to 5 times using an "
                "exponential backoff schedule:\n"
                "• Attempt 1: 5 seconds\n"
                "• Attempt 2: 30 seconds\n"
                "• Attempt 3: 2 minutes\n"
                "• Attempt 4: 15 minutes\n"
                "• Attempt 5: 1 hour\n\n"
                "If your endpoint remains down after all 5 retries, the webhook subscription will be temporarily "
                "disabled, and an incident alert will be sent to your account administrator. Once your service recovers, "
                "you can manually replay failed deliveries directly from Developer Settings > Webhooks > Dead Letter Queue.\n\n"
                "Let us know if you need assistance debugging the webhook headers!\n\n"
                "— OmniTriage Technical Operations (Reference: docs://webhook_retries.md)"
            )
        elif "secret" in t_low and ("api" in t_low or "reset" in t_low or "lost" in t_low):
            return (
                "Hi there,\n\nFor cryptographic security, OmniTriage stores only salted SHA-256 hashes of secret API keys. "
                "As a result, our team and automated systems have zero capability to retrieve, view, or email your original secret key.\n\n"
                "To resolve this, your administrator should:\n"
                "1. Navigate to Settings > Developer > API Keys.\n"
                "2. Revoke the lost key to prevent unauthorized access.\n"
                "3. Generate a new secret key and immediately store it in your team's secret manager (e.g. AWS Secrets Manager or Doppler).\n\n"
                "Please let us know if you need help scoping permissions on your replacement key.\n\n"
                "— OmniTriage Security & Auth Team (Reference: docs://api_keys.md)"
            )
        elif "refund" in t_low and ("downgrade" in t_low or "seat" in t_low):
            return (
                "Hello,\n\nWhen a team member seat is downgraded or removed, the change takes effect immediately. "
                "Under our standard Terms of Service, the remaining unused value for that seat is converted into an account billing credit "
                "that automatically offsets future monthly subscription invoices. We do not provide direct cash refunds for seat downgrades.\n\n"
                "You can review your active credit balance anytime under Settings > Billing & Invoices.\n\n"
                "— OmniTriage Billing Team (Reference: docs://billing_faqs.md)"
            )
        else:
            return (
                "Hello,\n\nThank you for reaching out. Based on your inquiry, we have referenced our internal developer specifications. "
                "To ensure you receive the most accurate resolution, we have packaged your ticket context and routed this inquiry directly "
                "to our senior engineering team. A technical representative will follow up within our standard business SLA.\n\n"
                "— OmniTriage Support Engine"
            )
