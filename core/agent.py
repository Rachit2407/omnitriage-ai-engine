import os
from typing import Dict, Any, List
from core.rag_engine import RAGEngine
from core.guardrails import GuardrailAuditor
from core.config import settings

class SupportTriageAgent:
    """
    Main orchestration agent:
    1. Embeds and retrieves relevant documentation chunks.
    2. Synthesizes a technical response with exact citations using Groq, Gemini, or OpenAI.
    3. Runs an adversarial guardrail audit.
    4. Routes the ticket (AUTO_RESOLVE_DISPATCH vs. ESCALATE_HUMAN_TIER_2).
    """
    def __init__(self, rag: RAGEngine, auditor: GuardrailAuditor):
        self.rag = rag
        self.auditor = auditor
        self.provider_name, self.api_key, self.model_name, self.base_url = settings.get_provider_details()
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                if self.base_url:
                    self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                else:
                    self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                print(f"[SupportTriageAgent] Client initialization failed: {e}")
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
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1
                )
                drafted_reply = response.choices[0].message.content
            except Exception as e:
                print(f"[SupportTriageAgent] LLM generation error ({self.provider_name}): {e}")
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
            "citations": [c['source'] for c in chunks],
            "provider": self.provider_name
        }

    def _generate_deterministic_reply(self, ticket: str, chunks: List[Dict[str, Any]]) -> str:
        """Deterministic high-fidelity response generator for demo without active API key."""
        t_low = ticket.lower()
        if "webhook" in t_low or "retry" in t_low:
            return (
                "Hi there,\n\nOur system automatically retries failed webhook deliveries (any HTTP status other than 200) "
                "up to 5 times using an exponential backoff schedule:\n"
                "• 1st retry: 5 seconds\n"
                "• 2nd retry: 30 seconds\n"
                "• 3rd retry: 2 minutes\n"
                "• 4th retry: 15 minutes\n"
                "• 5th retry: 1 hour\n\n"
                "If the destination endpoint does not return a 200 after all 5 retries, the webhook is automatically "
                "paused and a notification is dispatched to your admin email address.\n\n"
                "Reference: docs://webhook_retries.md"
            )
        elif "secret" in t_low or "api key" in t_low:
            return (
                "Hi there,\n\nFor security and compliance reasons, secret API keys are generated once and hashed with SHA-256. "
                "They are never stored in plaintext and cannot be recovered or retrieved by any member of our team.\n\n"
                "To restore service for your application:\n"
                "1. Navigate to Settings > Developer Keys in your dashboard.\n"
                "2. Generate a new secret key with the necessary scoped permissions.\n"
                "3. Update your production environment variables.\n"
                "4. Revoke the lost key to prevent unauthorized usage.\n\n"
                "Reference: docs://api_keys.md"
            )
        elif "refund" in t_low or "downgrad" in t_low:
            return (
                "Hi there,\n\nPer our enterprise subscription terms, seats removed mid-cycle are not eligible for direct cash refunds "
                "back to credit cards. Instead, the unused prorated balance is automatically converted into account credits that will "
                "apply toward your next monthly billing cycle.\n\n"
                "Reference: docs://billing_faqs.md"
            )
        else:
            return (
                f"Thank you for reaching out. Based on our documentation:\n\n"
                f"{chunks[0]['content'] if chunks else 'Ticket flagged for engineering review.'}\n\n"
                "Please let us know if you have any follow-up questions."
            )
