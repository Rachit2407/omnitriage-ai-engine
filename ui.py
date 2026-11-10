import streamlit as st
import os
import sys

# Ensure core package is on path
sys.path.append(os.path.dirname(__file__))

from core.config import settings
from core.auth import auth_manager
from core.doc_crawler import doc_crawler
from core.rag_engine import RAGEngine
from core.guardrails import GuardrailAuditor
from core.agent import SupportTriageAgent

st.set_page_config(
    page_title="OmniTriage AI | Multi-Tenant Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Enterprise Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #0f172a;
        color: #f8fafc;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        border-left: 4px solid #2563eb;
    }
    .badge-pass {
        background-color: #dcfce7;
        color: #166534;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .badge-escalate {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 6px 14px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
    }
    .code-box {
        background-color: #0f172a;
        color: #38bdf8;
        padding: 12px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_system():
    rag = RAGEngine()
    kb_path = os.path.join(os.path.dirname(__file__), "data", "sample_knowledge_base")
    rag.load_local_knowledge_base(kb_path, tenant_id="tenant_default_demo")
    auditor = GuardrailAuditor()
    agent = SupportTriageAgent(rag, auditor)
    return agent, rag

agent, rag = initialize_system()

# Multi-Tenant Session State Initialization
if "current_tenant_id" not in st.session_state:
    st.session_state.current_tenant_id = "tenant_default_demo"

# Fetch active tenant details
active_tenant = auth_manager.get_tenant_by_id(st.session_state.current_tenant_id)
if not active_tenant:
    active_tenant = auth_manager.list_all_tenants()[0]
    st.session_state.current_tenant_id = active_tenant["id"]

# Sidebar: Tenant Switcher, Profile & Telemetry
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/lightning-bolt.png", width=60)
    st.title("OmniTriage AI")
    st.caption("Multi-Tenant Autonomous Support & Guardrails")
    st.divider()

    st.markdown("### 🏢 Active Workspace")
    tenants = auth_manager.list_all_tenants()
    tenant_options = {f"{t['company_name']} ({t['id'][:12]}...)": t['id'] for t in tenants}
    
    current_label = next((k for k, v in tenant_options.items() if v == st.session_state.current_tenant_id), list(tenant_options.keys())[0])
    selected_label = st.selectbox("Switch SaaS Tenant:", list(tenant_options.keys()), index=list(tenant_options.keys()).index(current_label))
    
    if tenant_options[selected_label] != st.session_state.current_tenant_id:
        st.session_state.current_tenant_id = tenant_options[selected_label]
        st.rerun()

    active_tenant = auth_manager.get_tenant_by_id(st.session_state.current_tenant_id)
    doc_count = rag.get_tenant_doc_count(active_tenant["id"])

    st.markdown(f"**Tenant ID:** `{active_tenant['id']}`")
    st.markdown(f"**Indexed Chunks:** `{doc_count}`")
    st.markdown(f"**Active LLM:** `{agent.provider_name}`")
    st.markdown(f"**API Key:** `{active_tenant['api_key'][:10]}...`")
    st.divider()

    st.markdown("### 🛡️ Enterprise SLA Guarantees")
    st.markdown("✔️ **Tenant Vector Partitioning**")
    st.markdown("✔️ **0% Hallucination Guardrail**")
    st.markdown("✔️ **Deterministic Escalation**")
    st.markdown("✔️ **Citation Verification**")

# Main Header
st.title("⚡ OmniTriage AI: Multi-Tenant Platform")
st.markdown(
    f"Currently logged into **{active_tenant['company_name']}** workspace. "
    "Triage customer support tickets with **0% hallucination risk** backed by your official documentation."
)

# Main Navigation Tabs
tab_ingest, tab_triage, tab_widget, tab_auth = st.tabs([
    "📥 1-Click Documentation Ingestion",
    "🧪 Live Triage & Guardrail Testing",
    "🔌 Embeddable Chat Widget & Slack",
    "🏢 Multi-Tenant Auth & Settings"
])

# ================= TAB 1: 1-CLICK DOC INGESTION ================= #
with tab_ingest:
    st.subheader("🌐 Ingest Your Public Documentation in 60 Seconds")
    st.markdown("Enter your SaaS public docs URL (e.g. `docs.yourcompany.com`). Our engine crawls pages, extracts clean text, and indexes semantic chunks into your private tenant partition.")

    col_url, col_btn = st.columns([3, 1])
    with col_url:
        docs_url_input = st.text_input(
            "Documentation URL:",
            value=active_tenant.get("docs_url") or "https://docs.github.com/en/rest",
            placeholder="https://docs.company.com"
        )
    with col_btn:
        st.write("")
        st.write("")
        crawl_btn = st.button("🚀 Crawl & Ingest Docs", type="primary", use_container_width=True)

    if crawl_btn and docs_url_input.strip():
        with st.status("🔍 Crawling documentation & building semantic vector index...", expanded=True) as status:
            st.write(f"1. Fetching base URL `{docs_url_input}`...")
            chunks = doc_crawler.crawl_and_chunk(
                start_url=docs_url_input.strip(),
                tenant_id=active_tenant["id"],
                chunk_words=350
            )
            
            if chunks:
                st.write(f"2. Extracted {len(chunks)} clean semantic chunks across internal subpages.")
                st.write(f"3. Ingesting into tenant partition `{active_tenant['id']}`...")
                rag.ingest_documents(chunks, tenant_id=active_tenant["id"])
                
                auth_manager.update_tenant_settings(
                    tenant_id=active_tenant["id"],
                    docs_url=docs_url_input.strip(),
                    indexed_pages_count=len(chunks)
                )
                status.update(label=f"✅ Successfully indexed {len(chunks)} chunks into your knowledge base!", state="complete")
                st.success(f"Documentation from {docs_url_input} is now live and isolated for {active_tenant['company_name']}!")
            else:
                status.update(label="⚠️ Unable to fetch pages from target URL. Please verify URL is public.", state="error")

    st.divider()
    st.markdown("#### 📚 Current Tenant Knowledge Base Preview")
    current_docs = [d for d in rag.documents if d.get("tenant_id") == active_tenant["id"]]
    if current_docs:
        st.markdown(f"**Total Indexed Chunks:** `{len(current_docs)}`")
        for idx, doc in enumerate(current_docs[:4]):
            with st.expander(f"📄 [{doc.get('title', 'Documentation')}] - Source: {doc.get('source', '')}"):
                st.write(doc["text"])
    else:
        st.info("No documents indexed for this tenant yet. Ingest your docs URL above or switch to Acme Platform to test pre-seeded docs.")

# ================= TAB 2: LIVE TRIAGE & GUARDRAIL TESTING ================= #
with tab_triage:
    st.subheader(f"🧪 Test OmniTriage on {active_tenant['company_name']}'s Knowledge Base")
    st.markdown("Submit customer inquiries. The engine searches your indexed docs, drafts answers, and performs a real-time hallucination audit.")

    col_in, col_out = st.columns([1, 1], gap="large")

    with col_in:
        scenario = st.selectbox(
            "Load realistic ticket scenario or test custom:",
            [
                "Webhook Outage & Retry Intervals",
                "Secret API Key Lost Recovery Request",
                "Seat Downgrade & Refund Inquiry",
                "Custom Support Ticket"
            ]
        )

        if scenario == "Webhook Outage & Retry Intervals":
            default_t = "Our webhook endpoint was down for 10 minutes. How many times does your system retry before giving up?"
        elif scenario == "Secret API Key Lost Recovery Request":
            default_t = "We lost our production secret API key. Can you retrieve it from your database and email it to us?"
        elif scenario == "Seat Downgrade & Refund Inquiry":
            default_t = "Can we get a cash refund to our credit card for unused seats after downgrading our subscription?"
        else:
            default_t = ""

        ticket_input = st.text_area("Customer Support Ticket:", value=default_t, height=160, placeholder="Type inquiry here...")
        process_btn = st.button("🚀 Process Ticket Through Pipeline", type="primary", use_container_width=True)

    with col_out:
        if process_btn and ticket_input.strip():
            with st.spinner("Executing tenant retrieval & guardrail evaluation..."):
                res = agent.process_ticket(
                    user_ticket=ticket_input,
                    tenant_id=active_tenant["id"],
                    tenant_name=active_tenant["company_name"],
                    slack_webhook_url=active_tenant.get("slack_webhook_url")
                )

            verdict = res["verdict"]
            status = res["status"]

            if status == "RESOLVED":
                st.markdown(f'<div class="badge-pass">✅ {res["recommended_action"]} (Confidence: {verdict["confidence_score"]*100:.1f}%)</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="badge-escalate">⚠️ {res["recommended_action"]} (Confidence: {verdict["confidence_score"]*100:.1f}%)</div>', unsafe_allow_html=True)

            st.markdown(f"**Target Routing:** `{res['routed_to']}`")
            st.markdown("#### 💬 Synthesized Reply:")
            st.info(res["drafted_reply"])

            with st.expander("🔍 Guardrail & Citation Telemetry", expanded=True):
                m1, m2, m3 = st.columns(3)
                m1.metric("Grounded in Docs", "YES" if verdict["is_grounded"] else "NO")
                m2.metric("Hallucinations", "NONE" if not verdict["contains_hallucination"] else "DETECTED")
                m3.metric("Confidence", f"{verdict['confidence_score']*100:.1f}%")

                st.markdown(f"**Reasoning:** {verdict['reasoning']}")
                st.markdown(f"**Citations:** `{', '.join(res['citations'])}`")
        else:
            st.info("👈 Enter a ticket inquiry and click 'Process Ticket' to inspect live execution.")

# ================= TAB 3: EMBED WIDGET & SLACK ================= #
with tab_widget:
    st.subheader("🔌 1-Line Embeddable Chat Widget")
    st.markdown("Paste this single line of JavaScript into your website before the closing `</body>` tag to instantly add OmniTriage AI to your customer-facing product:")

    embed_snippet = f'<script src="https://omnitriage-demo.streamlit.app/static/widget.js" data-tenant-id="{active_tenant["id"]}" data-company="{active_tenant["company_name"]}"></script>'
    
    st.code(embed_snippet, language="html")

    st.markdown("#### 🖥️ Live Widget Preview")
    st.markdown("Preview the widget functionality directly on our simulation portal or embed it into your app:")
    st.link_button("🌐 Open Interactive Live Widget Test Page", "https://omnitriage-demo.streamlit.app/widget/preview")

    st.divider()

    st.subheader("📢 Slack Escalation Webhook Integration")
    st.markdown("When the AI encounters an ungrounded or high-risk ticket, it automatically sends a rich pre-drafted summary to your Slack channel so your human support team can respond in 1 click.")

    slack_input = st.text_input(
        "Slack Incoming Webhook URL:",
        value=active_tenant.get("slack_webhook_url") or "",
        placeholder="https://hooks.slack.com/services/T000/B000/XXXX"
    )
    if st.button("💾 Save Slack Webhook URL"):
        auth_manager.update_tenant_settings(active_tenant["id"], slack_webhook_url=slack_input.strip())
        st.success("Slack Webhook URL saved successfully!")

# ================= TAB 4: MULTI-TENANT AUTH & SETTINGS ================= #
with tab_auth:
    st.subheader("🏢 Register New SaaS Founder Workspace")
    st.markdown("Sign up a new B2B SaaS company. Each workspace receives an isolated vector partition, API key, and custom widget snippet.")

    with st.form("signup_form"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            new_email = st.text_input("Founder Email Address*", placeholder="founder@company.com")
            new_company = st.text_input("Company Name*", placeholder="Stripe / PostHog / Supabase")
        with col_f2:
            new_password = st.text_input("Password*", type="password", placeholder="••••••••")
            new_docs_url = st.text_input("Public Docs URL (optional):", placeholder="https://docs.company.com")

        submit_signup = st.form_submit_button("🚀 Create Dedicated SaaS Workspace", type="primary")

        if submit_signup:
            if not new_email or not new_company or not new_password:
                st.error("Please fill in email, company name, and password.")
            else:
                try:
                    new_tenant = auth_manager.create_tenant(
                        email=new_email,
                        company_name=new_company,
                        password=new_password,
                        docs_url=new_docs_url
                    )
                    st.session_state.current_tenant_id = new_tenant["id"]
                    st.success(f"Workspace created for {new_company}! Tenant ID: {new_tenant['id']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign up error: {e}")

    st.divider()
    st.markdown("#### 🔑 Active Workspace Credentials")
    st.json({
        "tenant_id": active_tenant["id"],
        "company_name": active_tenant["company_name"],
        "email": active_tenant["email"],
        "api_key": active_tenant["api_key"],
        "docs_url": active_tenant.get("docs_url"),
        "slack_webhook_connected": bool(active_tenant.get("slack_webhook_url"))
    })
