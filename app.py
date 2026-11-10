from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import os
import sys

sys.path.append(os.path.dirname(__file__))

from core.rag_engine import RAGEngine
from core.guardrails import GuardrailAuditor
from core.agent import SupportTriageAgent

app = FastAPI(
    title="OmniTriage AI API",
    description="Enterprise webhook middleware for autonomous B2B support triage and guardrailed ticket resolution.",
    version="1.0.0"
)

# Initialize engine on startup
rag = RAGEngine()
kb_path = os.path.join(os.path.dirname(__file__), "data", "sample_knowledge_base")
rag.load_local_knowledge_base(kb_path)
auditor = GuardrailAuditor()
agent = SupportTriageAgent(rag, auditor)

class InboundTicketPayload(BaseModel):
    ticket_id: str = Field(description="Unique identifier from Zendesk/Intercom/Slack")
    customer_email: str = Field(description="Sender email address")
    message_text: str = Field(description="Body of the customer support request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom enterprise metadata")

class TriageResponse(BaseModel):
    ticket_id: str
    status: str
    action: str
    routed_to: str
    confidence_score: float
    reply_body: str
    citations: List[str]

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "omnitriage-ai-engine",
        "indexed_documents": len(rag.documents),
        "guardrail_status": "active"
    }

@app.post("/api/v1/triage", response_model=TriageResponse)
def triage_ticket_endpoint(payload: InboundTicketPayload):
    """
    Webhook endpoint to ingest an inbound support ticket, execute RAG retrieval,
    perform safety guardrail auditing, and output the recommended action.
    """
    if not payload.message_text.strip():
        raise HTTPException(status_code=400, detail="Ticket message_text cannot be empty.")

    result = agent.process_ticket(payload.message_text)

    return TriageResponse(
        ticket_id=payload.ticket_id,
        status=result["status"],
        action=result["recommended_action"],
        routed_to=result["routed_to"],
        confidence_score=result["verdict"]["confidence_score"],
        reply_body=result["drafted_reply"],
        citations=result["citations"]
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
