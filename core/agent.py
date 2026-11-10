import os
import requests
from typing import Dict, Any, List, Optional
from core.rag_engine import RAGEngine
from core.guardrails import GuardrailAuditor
from core.config import settings

class SupportTriageAgent:
    """
    Tenant-Aware Autonomous Triage Agent:
    1. Embeds and retrieves documentation chunks isolated to the specific tenant.
    2. Synthesizes a technical response with exact documentation citations.
    3. Runs an adversarial guardrail audit (hallucination & policy check).
    4. Routes the ticket (AUTO_RESOLVE_SENT vs. ESCALATE_TO_HUMAN_TIER_2).
    5. Dispatches real-time Slack escalation alerts when webhooks are connected.
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

    def process_ticket(
        self,
        user_ticket: str,
        tenant_id: str = "tenant_default_demo",
        tenant_name: str = "Acme Developer Platform",
        slack_webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        # Step 1: Context Retrieval isolated to tenant's knowledge base
        chunks = self.rag.retrieve_context(user_ticket, tenant_id=tenant_id, top_k=2)
        context_str = "\n\n".join([f"Source ({c['source']}) - {c.get('title', '')}:\n{c['content']}" for c in chunks])

        # Step 2: Synthesis
        if self.client and context_str.strip():
            system_prompt = (
                f"You are the Lead Technical Support AI for {tenant_name}. "
                "Resolve the customer's inquiry with extreme precision, citing exact documentation rules. "
                "Never invent policies, parameters, or features not explicitly backed by the provided documentation. "
                "If the documentation does not permit an action or if context is missing, explain the policy "
                "clearly and politely inform the user that the request is flagged for senior engineering review."
            )
            user_prompt = f"Official Knowledge Base Context:\n{context_str}\n\nCustomer Support Ticket:\n{user_ticket}"
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

        # Step 4: Decision Routing & SLA Assignment
        if verdict.can_safely_send:
            action = "AUTO_RESOLVE_SENT"
            status = "RESOLVED"
            routed_to = "Customer Inbox (Automated SLA < 2s)"
        else:
            action = "ESCALATE_TO_HUMAN_TIER_2"
            status = "HUMAN_TRIAGE_REQUIRED"
            routed_to = f"{tenant_name} Senior Engineering Queue (High Priority)"

            # Step 5: Optional Slack Escalation Webhook Dispatch
            if slack_webhook_url:
                self._dispatch_slack_alert(
                    webhook_url=slack_webhook_url,
                    ticket=user_ticket,
                    verdict=verdict.model_dump(),
                    drafted_reply=drafted_reply,
                    tenant_name=tenant_name
                )

        return {
            "ticket": user_ticket,
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "drafted_reply": drafted_reply,
            "verdict": verdict.model_dump(),
            "recommended_action": action,
            "status": status,
            "routed_to": routed_to,
            "citations": [c['source'] for c in chunks],
            "provider": self.provider_name
        }

    def _dispatch_slack_alert(
        self,
        webhook_url: str,
        ticket: str,
        verdict: Dict[str, Any],
        drafted_reply: str,
        tenant_name: str
    ):
        """Dispatches rich Slack block kit alert for tickets requiring human attention."""
        try:
            payload = {
                "text": f"🚨 OmniTriage Escalation: {tenant_name} Support Queue",
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "🚨 Human Escalation Required", "emoji": True}
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Company:* {tenant_name}"},
                            {"type": "mrkdwn", "text": f"*Confidence:* {verdict.get('confidence_score', 0)*100:.1f}%"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Customer Ticket:*\n> {ticket}"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Guardrail Flag Reason:*\n_{verdict.get('reasoning')}_"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Pre-Drafted Diagnostic Summary:*\n```{drafted_reply[:400]}...```"}
                    }
                ]
            }
            requests.post(webhook_url, json=payload, timeout=3)
        except Exception as e:
            print(f"[SupportTriageAgent] Slack dispatch error: {e}")

    def _generate_deterministic_reply(self, ticket: str, chunks: List[Dict[str, Any]]) -> str:
        """Deterministic high-fidelity response generator for fallback or testing."""
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
        elif chunks:
            return (
                f"Thank you for contacting support. Based on our verified documentation:\n\n"
                f"{chunks[0]['content'][:600]}\n\n"
                f"Source: {chunks[0]['source']}"
            )
        else:
            return (
                "Thank you for your inquiry. This specific question requires verification with our engineering team. "
                "I have flagged this ticket with high priority for a specialist to review."
            )
