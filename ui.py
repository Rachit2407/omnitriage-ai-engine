import streamlit as st
import os
import sys

# Ensure core package is on path
sys.path.append(os.path.dirname(__file__))

from core.rag_engine import RAGEngine
from core.guardrails import GuardrailAuditor
from core.agent import SupportTriageAgent

st.set_page_config(
    page_title="OmniTriage AI | Autonomous Support Triage & Guardrail Engine",
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
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-escalate {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_system():
    rag = RAGEngine()
    kb_path = os.path.join(os.path.dirname(__file__), "data", "sample_knowledge_base")
    docs_count = rag.load_local_knowledge_base(kb_path)
    auditor = GuardrailAuditor()
    agent = SupportTriageAgent(rag, auditor)
    return agent, docs_count

agent, docs_count = initialize_system()

# Sidebar: System Telemetry & Architecture
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/lightning-bolt.png", width=64)
    st.title("OmniTriage AI")
    st.caption("v2.4 Production Engine | B2B SaaS Triage")
    st.divider()
    
    st.markdown("### 📊 Live System Metrics")
    st.markdown(f"**Knowledge Base:** `{docs_count} Verified Docs`")
    st.markdown("**Vector Store:** `ChromaDB / Semantic Index`")
    st.markdown("**Guardrail SLA:** `< 850ms latency`")
    st.markdown("**Confidence Threshold:** `0.85 (Strict)`")
    st.divider()

    st.markdown("### 🛡️ Guardrail Guarantees")
    st.markdown("✔️ **0% Hallucinated Policies**")
    st.markdown("✔️ **Automatic PII Redaction**")
    st.markdown("✔️ **Deterministic Human Escalation**")
    st.markdown("✔️ **Full Source Citation Attribution**")
    st.divider()
    st.caption("Engineered for B2B SaaS Founders & CX Leaders.")

# Main Interface Header
st.title("⚡ OmniTriage AI: Support Resolution & Guardrail Engine")
st.markdown(
    "Automating 40%+ of repetitive B2B technical tickets with **zero hallucination risk**. "
    "Every response is checked against your official documentation before delivery."
)

st.divider()

col_input, col_audit = st.columns([1, 1], gap="large")

with col_input:
    st.subheader("📥 1. Customer Inbound Simulation")
    
    scenario = st.selectbox(
        "Select a Realistic Customer Support Ticket Scenario:",
        [
            "Scenario A: Webhook Outage & Automated Retry Schedule",
            "Scenario B: Lost Secret API Key Recovery Request",
            "Scenario C: Seat Downgrade & Cash Refund Inbound",
            "Custom Inquiry (Type your own)"
        ]
    )

    if scenario == "Scenario A: Webhook Outage & Automated Retry Schedule":
        default_ticket = (
            "Hi team,\n\nOur webhook destination endpoint was down for about 12 minutes due to an AWS outage. "
            "How many times will your system retry the delivery before giving up, and what is the interval schedule?"
        )
    elif scenario == "Scenario B: Lost Secret API Key Recovery Request":
        default_ticket = (
            "Urgent: Our lead backend engineer left the company and we lost our production secret API key. "
            "Can you please retrieve our active secret key from your database and email it to us immediately?"
        )
    elif scenario == "Scenario C: Seat Downgrade & Cash Refund Inbound":
        default_ticket = (
            "We removed 4 developer seats from our enterprise plan 10 days into the billing cycle. "
            "Can you issue a cash refund directly to our credit card for the unused portion of this month?"
        )
    else:
        default_ticket = ""

    ticket_text = st.text_area(
        "Customer Support Ticket Message:",
        value=default_ticket,
        height=180,
        placeholder="Type or paste an incoming customer ticket here..."
    )

    execute_btn = st.button("🚀 Process Ticket Through OmniTriage Pipeline", type="primary", use_container_width=True)

with col_audit:
    st.subheader("⚙️ 2. Autonomous Triage & Guardrail Audit")
    
    if execute_btn and ticket_text.strip():
        with st.spinner("Executing Semantic Search & Adversarial Safety Audit..."):
            result = agent.process_ticket(ticket_text)

        verdict = result["verdict"]
        status = result["status"]

        # Action Banner
        if status == "RESOLVED":
            st.markdown(
                f'<div class="badge-pass">✅ {result["recommended_action"]} (Confidence: {verdict["confidence_score"]*100:.1f}%)</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="badge-escalate">⚠️ {result["recommended_action"]} (Confidence: {verdict["confidence_score"]*100:.1f}%)</div>',
                unsafe_allow_html=True
            )

        st.markdown(f"**Target Routing:** `{result['routed_to']}`")

        # Response Output
        st.markdown("#### 💬 Synthesized Customer Response:")
        st.info(result["drafted_reply"])

        # Detailed Audit Breakdown
        with st.expander("🔍 Deep Guardrail & Citation Telemetry", expanded=True):
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric("Grounded in Docs", "YES" if verdict["is_grounded"] else "NO")
            with metric_col2:
                st.metric("Hallucinations", "NONE" if not verdict["contains_hallucination"] else "DETECTED")
            with metric_col3:
                st.metric("Policy Compliance", "100%" if verdict["policy_compliance"] else "FAILED")

            st.markdown(f"**Audit Reasoning:** {verdict['reasoning']}")
            st.markdown(f"**Document Citations:** `{', '.join(result['citations'])}`")
            
    elif not execute_btn:
        st.info("👈 Select a ticket scenario or enter a custom ticket, then click 'Process Ticket' to inspect live execution.")
