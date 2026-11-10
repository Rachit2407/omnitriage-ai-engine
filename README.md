# ⚡ OmniTriage AI: Autonomous Support & Guardrailed Triage Engine

> **Production-grade RAG support resolution engine with real-time hallucination scoring and deterministic policy enforcement for B2B SaaS.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-FF4B4B.svg?style=flat&logo=streamlit)](https://streamlit.io)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2.9-E92063.svg?style=flat&logo=pydantic)](https://docs.pydantic.dev)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat&logo=python)](https://python.org)

---

## 🎯 The Core Business Problem

High-growth B2B software companies ($1M–$10M ARR) handle hundreds of incoming technical support tickets every week. 
Over **40% of tier-1 support inquiries** are repetitive:
- *"What is your webhook retry interval schedule?"*
- *"Can you recover or email our production secret API key?"*
- *"Can we get a cash refund for seats downgraded mid-cycle?"*

Standard LLM chatbots **hallucinate policies, invent non-existent refund guarantees, or attempt to disclose unrecoverable security credentials**.

**OmniTriage AI solves this with an Adversarial Safety Guardrail Layer**:
Every drafted response is audited in real-time against verified documentation chunks using structured Pydantic schemas. If confidence drops below `0.85` or a policy violation is detected, **auto-dispatch is halted and the ticket is routed directly to human tier-2 support with an enriched diagnostic summary.**

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          OMNITRIAGE AI ARCHITECTURE                             │
│                                                                                 │
│  [Customer Inbound Ticket]                                                      │
│             │                                                                   │
│             ▼                                                                   │
│  [FastAPI / LangGraph Orchestrator]                                             │
│             │                                                                   │
│             ├─► [1. Query Embedding] ──► [ChromaDB / Pinecone Vector Store]     │
│             │                                     │                             │
│             │                                     ▼                             │
│             │                          [Relevant Doc Chunks]                    │
│             │                                     │                             │
│             ├─► [2. LLM Synthesis with Exact Citations]                         │
│             │                                     │                             │
│             ▼                                     ▼                             │
│  [3. Guardrail Auditor] ◄─────────────────────────┘                             │
│     • Check Confidence Score (> 0.85)                                           │
│     • Hallucination Verification vs Docs                                        │
│     • Cryptographic & Policy Compliance Filter                                  │
│             │                                                                   │
│             ├───► [PASS] ──► Auto-Reply to Customer with Doc Deep Links         │
│             │                                                                   │
│             └───► [FAIL] ──► Escalate to Tier-2 Queue with Formatted JSON       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart & Local Setup

### 1. Clone & Navigate
```bash
git clone https://github.com/[your-username]/omnitriage-ai-engine.git
cd omnitriage-ai-engine
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env and insert your OPENAI_API_KEY (optional for local deterministic demo)
```

### 4. Launch Interactive Demo (Streamlit)
```bash
streamlit run ui.py
```
*Access the interactive testing workbench at `http://localhost:8501`.*

### 5. Launch Production API (FastAPI)
```bash
python app.py
# or: uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
*Access interactive Swagger API docs at `http://localhost:8000/docs`.*

---

## 📡 API Usage Example (Webhook Ingestion)

### Request:
```bash
curl -X POST "http://localhost:8000/api/v1/triage" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TCK-8921",
    "customer_email": "cto@acmefinance.io",
    "message_text": "Our webhook receiver was offline. What is your automatic retry schedule before disabling the endpoint?"
  }'
```

### Response (200 OK):
```json
{
  "ticket_id": "TCK-8921",
  "status": "RESOLVED",
  "action": "AUTO_RESOLVE_SENT",
  "routed_to": "Customer Inbox (Automated SLA < 2s)",
  "confidence_score": 0.98,
  "reply_body": "Hello,\n\nOur system automatically retries failed webhook deliveries up to 5 times using an exponential backoff schedule: 5s, 30s, 2m, 15m, and 1 hour...",
  "citations": [
    "docs://webhook_retries.md"
  ]
}
```

---

## 💼 Turnkey Deployment for B2B SaaS

Need this exact pipeline deployed into your existing Zendesk, Intercom, or Slack workflows?
- **Delivery Time:** 5 to 7 business days
- **Scope:** Custom documentation vector ingestion, CRM webhook middleware, brand tone calibration, staging validation suite.
- **Book Technical Audit:** [Schedule 15-min Architecture Sync](https://cal.com)
