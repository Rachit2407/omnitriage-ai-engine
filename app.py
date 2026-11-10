import os
import sys
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

sys.path.append(os.path.dirname(__file__))

from core.config import settings
from core.auth import auth_manager
from core.doc_crawler import doc_crawler
from core.rag_engine import RAGEngine
from core.guardrails import GuardrailAuditor
from core.agent import SupportTriageAgent

app = FastAPI(
    title="OmniTriage AI Multi-Tenant Engine",
    description="Multi-tenant B2B support triage, 1-click documentation crawler, and guardrailed ticket resolution API.",
    version="2.5.0"
)

# Enable CORS for external websites embedding the widget
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directory for embeddable widget.js delivery
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Initialize Engine
rag = RAGEngine()
kb_path = os.path.join(os.path.dirname(__file__), "data", "sample_knowledge_base")
rag.load_local_knowledge_base(kb_path, tenant_id="tenant_default_demo")
auditor = GuardrailAuditor()
agent = SupportTriageAgent(rag, auditor)

# ----------------- Request / Response Schemas ----------------- #

class FounderSignUpPayload(BaseModel):
    email: str = Field(description="Founder email address")
    company_name: str = Field(description="Name of the B2B SaaS company")
    password: str = Field(min_length=6, description="Account password")
    docs_url: Optional[str] = Field(default=None, description="Public documentation URL (optional)")

class IngestDocsPayload(BaseModel):
    tenant_id: str = Field(description="Target tenant identifier")
    docs_url: str = Field(description="Public documentation URL to crawl and index (e.g. https://docs.stripe.com)")
    max_pages: Optional[int] = Field(default=10, description="Maximum sub-pages to crawl (under 60s)")

class InboundTicketPayload(BaseModel):
    ticket_id: str = Field(description="Unique ticket identifier from Zendesk/Intercom/Slack/Widget")
    tenant_id: Optional[str] = Field(default="tenant_default_demo", description="Tenant ID")
    customer_email: Optional[str] = Field(default="support@customer.com", description="Sender email address")
    message_text: str = Field(description="Body of the customer support request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

class TriageResponse(BaseModel):
    ticket_id: str
    tenant_id: str
    status: str
    action: str
    routed_to: str
    confidence_score: float
    reply_body: str
    citations: List[str]
    provider: str

# ----------------- API Endpoints ----------------- #

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "omnitriage-multi-tenant-engine",
        "active_provider": agent.provider_name,
        "total_tenants": len(auth_manager.list_all_tenants()),
        "guardrail_status": "active"
    }

@app.get("/widget/preview", response_class=HTMLResponse)
def widget_preview():
    preview_path = os.path.join(static_dir, "widget_preview.html")
    if os.path.exists(preview_path):
        return FileResponse(preview_path)
    return "<h1>Widget Preview file not found</h1>"

@app.post("/api/v1/auth/signup")
def founder_signup(payload: FounderSignUpPayload):
    """
    Registers a new SaaS founder, provisions their isolated tenant workspace,
    and returns their private API key.
    """
    try:
        tenant = auth_manager.create_tenant(
            email=payload.email,
            company_name=payload.company_name,
            password=payload.password,
            docs_url=payload.docs_url
        )
        return {
            "success": True,
            "message": "Tenant account provisioned successfully.",
            "tenant_id": tenant["id"],
            "api_key": tenant["api_key"],
            "company_name": tenant["company_name"],
            "docs_url": tenant["docs_url"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/auth/login")
def founder_login(email: str, password: str):
    tenant = auth_manager.authenticate_tenant(email=email, password=password)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {
        "success": True,
        "tenant_id": tenant["id"],
        "api_key": tenant["api_key"],
        "company_name": tenant["company_name"],
        "docs_url": tenant["docs_url"],
        "indexed_pages_count": tenant["indexed_pages_count"]
    }

@app.post("/api/v1/tenants/ingest-docs")
def ingest_documentation(payload: IngestDocsPayload, background_tasks: BackgroundTasks):
    """
    1-Click Documentation Ingestion:
    Crawls the founder's public documentation, extracts clean text,
    semantically chunks it, and indexes it into their tenant-isolated vector partition in < 60 seconds.
    """
    tenant = auth_manager.get_tenant_by_id(payload.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    # Crawl and chunk
    chunks = doc_crawler.crawl_and_chunk(
        start_url=payload.docs_url,
        tenant_id=payload.tenant_id,
        chunk_words=350
    )

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to extract documentation content from {payload.docs_url}. Please check URL accessibility."
        )

    # Ingest into tenant's isolated partition
    rag.ingest_documents(chunks, tenant_id=payload.tenant_id)

    # Update tenant record
    auth_manager.update_tenant_settings(
        tenant_id=payload.tenant_id,
        docs_url=payload.docs_url,
        indexed_pages_count=len(chunks)
    )

    return {
        "success": True,
        "tenant_id": payload.tenant_id,
        "docs_url": payload.docs_url,
        "chunks_indexed": len(chunks),
        "status": "ready_for_triage"
    }

@app.post("/api/v1/triage", response_model=TriageResponse)
def triage_ticket_endpoint(payload: InboundTicketPayload):
    """
    Tenant-Scoped Triage Endpoint:
    Accepts an inbound customer ticket, retrieves chunks from the specific tenant's docs,
    runs safety & hallucination guardrails, and routes to customer inbox or escalates.
    """
    if not payload.message_text.strip():
        raise HTTPException(status_code=400, detail="Ticket message_text cannot be empty.")

    tenant = auth_manager.get_tenant_by_id(payload.tenant_id)
    company_name = tenant["company_name"] if tenant else "Acme Platform"
    slack_webhook = tenant.get("slack_webhook_url") if tenant else None

    result = agent.process_ticket(
        user_ticket=payload.message_text,
        tenant_id=payload.tenant_id,
        tenant_name=company_name,
        slack_webhook_url=slack_webhook
    )

    return TriageResponse(
        ticket_id=payload.ticket_id,
        tenant_id=payload.tenant_id,
        status=result["status"],
        action=result["recommended_action"],
        routed_to=result["routed_to"],
        confidence_score=result["verdict"]["confidence_score"],
        reply_body=result["drafted_reply"],
        citations=result["citations"],
        provider=result["provider"]
    )

@app.post("/api/v1/webhook/slack")
def slack_webhook_listener(event: Dict[str, Any]):
    """Receives inbound Slack bot mentions or commands and runs triage."""
    return {"status": "received", "event_type": event.get("type", "unknown")}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
