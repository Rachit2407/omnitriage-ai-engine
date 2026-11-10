# ⚡ OmniTriage AI: Multi-Tenant Autonomous Support & Guardrail Platform

> **Production-grade multi-tenant B2B support triage engine with 1-click documentation ingestion, 1-line embeddable chat widget, and real-time hallucination scoring.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-FF4B4B.svg?style=flat&logo=streamlit)](https://streamlit.io)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2.9-E92063.svg?style=flat&logo=pydantic)](https://docs.pydantic.dev)
[![Multi-Tenant](https://img.shields.io/badge/Multi--Tenant-Isolated-blue.svg)](#multi-tenant-architecture)
[![Groq & Gemini](https://img.shields.io/badge/Providers-Groq%20%7C%20Gemini%20%7C%20OpenAI-orange.svg)](#multi-provider-support)

---

## 🚀 Key New Capabilities

1. 🏢 **Multi-Tenant Workspace Partitioning (Supabase / Clerk / Local)**:
   - Any B2B SaaS founder can sign up with their email.
   - Each tenant receives an isolated vector partition, custom API key (`ot_live_...`), and dedicated customer support queue.
2. 🌐 **1-Click Documentation Ingestion (< 60s)**:
   - Founders paste their public documentation URL (e.g. `https://docs.stripe.com`, `https://docs.company.com`).
   - The built-in multi-threaded crawler extracts clean article text, semantically chunks it into ~350-word passages, and indexes it into the tenant's vector partition in under 60 seconds.
3. 🔌 **1-Line Embeddable JavaScript Widget**:
   - Founders embed the AI support bot into their web application with one line of JavaScript before `</body>`:
     ```html
     <script src="https://omnitriage-demo.streamlit.app/static/widget.js" data-tenant-id="YOUR_TENANT_ID" data-company="Your Company"></script>
     ```
   - Includes real-time citation badges, 0% hallucination guardrail indicators, and automatic fallback.
4. 📢 **Slack Escalation Webhook**:
   - Tickets requiring human intervention automatically dispatch a formatted alert to the founder's Slack channel with pre-drafted diagnostic summaries.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      OMNITRIAGE MULTI-TENANT ARCHITECTURE                       │
│                                                                                 │
│   [Founder Portal] ──► [1-Click Doc Crawler] ──► [Tenant-Isolated Vector Store] │
│                                                                │                │
│   [Customer Inbound / 1-Line Embed Widget / Slack]             │                │
│                        │                                       │                │
│                        ▼                                       ▼                │
│            [FastAPI / Tenant Middleware] ────────► [Tenant-Specific Context]    │
│                        │                                       │                │
│                        ▼                                       ▼                │
│            [Groq / Gemini / OpenAI Synthesis] ◄────────────────┘                │
│                        │                                                        │
│                        ▼                                                        │
│            [Pydantic Guardrail Auditor]                                         │
│               • Confidence Score (> 0.85)                                       │
│               • Hallucination Verification vs Docs                              │
│               • Cryptographic / Policy Compliance                               │
│                        │                                                        │
│             ┌──────────┴──────────┐                                             │
│             ▼                     ▼                                             │
│     [PASS: Confidence > 85%]  [FAIL / Ungrounded Policy]                        │
│     Auto-Resolve Customer     Escalate to Human Queue + Slack Webhook Alert     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Quickstart & Running Locally

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/Rachit2407/omnitriage-ai-engine.git
cd omnitriage-ai-engine
pip install -r requirements.txt
```

### 2. Configure Environment (Groq, Gemini, or OpenAI)
Create `.env` using `.env.example`:
```env
# Free tier Groq key (https://console.groq.com)
GROQ_API_KEY=gsk_your_groq_key

# Or free tier Gemini key (https://aistudio.google.com)
# GEMINI_API_KEY=AIzaSy_your_key

PORT=8000
```

### 3. Launch Dashboard & API
```bash
# Launch Multi-Tenant Streamlit Dashboard
streamlit run ui.py

# Or launch FastAPI Webhook / Widget Server
python app.py
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/auth/signup` | `POST` | Register a new SaaS founder & provision tenant API key |
| `/api/v1/auth/login` | `POST` | Authenticate founder and retrieve workspace credentials |
| `/api/v1/tenants/ingest-docs` | `POST` | 1-Click crawl & index public documentation in < 60s |
| `/api/v1/triage` | `POST` | Ingest ticket, run tenant RAG + Guardrails, and return verdict |
| `/api/v1/webhook/slack` | `POST` | Slack interactive webhook & event handler |
| `/widget/preview` | `GET` | Live interactive browser preview of the embeddable chat widget |

---

## 🛡️ Guardrail Guarantees
- **0% Hallucinated Policies**: If documentation does not support an action (e.g. recovering lost secret keys, granting unentitled refunds), auto-dispatch is halted.
- **Strict SLA**: Confidence threshold strictly set to `0.85`.
- **Tenant Isolation**: Inbound tickets query ONLY the documentation partition belonging to that tenant.
