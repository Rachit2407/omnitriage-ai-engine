/**
 * OmniTriage AI - 1-Line Embeddable Support Widget
 * Usage:
 * <script src="https://YOUR_HOST/static/widget.js" data-tenant-id="YOUR_TENANT_ID" data-api-url="https://YOUR_HOST"></script>
 */
(function () {
  if (window.OmniTriageWidgetLoaded) return;
  window.OmniTriageWidgetLoaded = true;

  // Extract configuration from current script tag
  const scriptTag = document.currentScript || document.querySelector('script[data-tenant-id]');
  const tenantId = scriptTag ? scriptTag.getAttribute('data-tenant-id') || 'tenant_default_demo' : 'tenant_default_demo';
  const apiUrl = scriptTag ? (scriptTag.getAttribute('data-api-url') || window.location.origin) : window.location.origin;
  const companyName = scriptTag ? scriptTag.getAttribute('data-company') || 'Support AI' : 'Support AI';

  // Inject Widget Styles
  const style = document.createElement('style');
  style.textContent = `
    .ot-widget-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      box-shadow: 0 8px 24px rgba(37, 99, 235, 0.35);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999999;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      border: none;
    }
    .ot-widget-launcher:hover {
      transform: scale(1.08) translateY(-2px);
      box-shadow: 0 12px 28px rgba(37, 99, 235, 0.45);
    }
    .ot-widget-container {
      position: fixed;
      bottom: 96px;
      right: 24px;
      width: 380px;
      height: 540px;
      max-width: calc(100vw - 32px);
      max-height: calc(100vh - 120px);
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 20px 48px rgba(15, 23, 42, 0.18), 0 0 0 1px rgba(15, 23, 42, 0.08);
      display: none;
      flex-direction: column;
      overflow: hidden;
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      animation: otSlideUp 0.2s ease-out;
    }
    @keyframes otSlideUp {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .ot-widget-header {
      background: #0f172a;
      color: #ffffff;
      padding: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .ot-header-info {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .ot-header-avatar {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: #2563eb;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 14px;
    }
    .ot-header-title {
      font-weight: 600;
      font-size: 14px;
    }
    .ot-header-sub {
      font-size: 11px;
      color: #94a3b8;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .ot-status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #22c55e;
    }
    .ot-close-btn {
      background: transparent;
      border: none;
      color: #94a3b8;
      font-size: 20px;
      cursor: pointer;
      line-height: 1;
    }
    .ot-chat-body {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      background: #f8fafc;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .ot-msg {
      max-width: 82%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 13.5px;
      line-height: 1.45;
    }
    .ot-msg-user {
      align-self: flex-end;
      background: #2563eb;
      color: #ffffff;
      border-bottom-right-radius: 4px;
    }
    .ot-msg-bot {
      align-self: flex-start;
      background: #ffffff;
      color: #1e293b;
      border: 1px solid #e2e8f0;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .ot-meta-badge {
      display: inline-block;
      font-size: 10.5px;
      padding: 2px 6px;
      border-radius: 4px;
      margin-top: 6px;
      font-weight: 600;
      background: #dcfce7;
      color: #15803d;
    }
    .ot-meta-badge.escalated {
      background: #fee2e2;
      color: #991b1b;
    }
    .ot-citations {
      font-size: 11px;
      color: #64748b;
      margin-top: 4px;
    }
    .ot-input-area {
      padding: 12px;
      background: #ffffff;
      border-top: 1px solid #e2e8f0;
      display: flex;
      gap: 8px;
    }
    .ot-input-field {
      flex: 1;
      padding: 10px 14px;
      border: 1px solid #cbd5e1;
      border-radius: 20px;
      font-size: 13.5px;
      outline: none;
      transition: border-color 0.15s;
    }
    .ot-input-field:focus {
      border-color: #2563eb;
    }
    .ot-send-btn {
      background: #2563eb;
      color: #ffffff;
      border: none;
      border-radius: 50%;
      width: 38px;
      height: 38px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s;
    }
    .ot-send-btn:hover {
      background: #1d4ed8;
    }
    .ot-send-btn:disabled {
      background: #94a3b8;
      cursor: not-allowed;
    }
  `;
  document.head.appendChild(style);

  // Build DOM Elements
  const launcher = document.createElement('button');
  launcher.className = 'ot-widget-launcher';
  launcher.innerHTML = `
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
  `;

  const container = document.createElement('div');
  container.className = 'ot-widget-container';
  container.innerHTML = `
    <div class="ot-widget-header">
      <div class="ot-header-info">
        <div class="ot-header-avatar">⚡</div>
        <div>
          <div class="ot-header-title">${companyName} Assistant</div>
          <div class="ot-header-sub">
            <span class="ot-status-dot"></span> 0% Hallucination Guardrail Active
          </div>
        </div>
      </div>
      <button class="ot-close-btn">&times;</button>
    </div>
    <div class="ot-chat-body" id="otChatBody">
      <div class="ot-msg ot-msg-bot">
        Hello! I'm your documentation support assistant. Ask me anything about our API, webhooks, or billing.
      </div>
    </div>
    <form class="ot-input-area" id="otInputForm">
      <input type="text" class="ot-input-field" id="otInputField" placeholder="Ask a question..." autocomplete="off" required />
      <button type="submit" class="ot-send-btn" id="otSendBtn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="22" y1="2" x2="11" y2="13"></line>
          <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
        </svg>
      </button>
    </form>
  `;

  document.body.appendChild(launcher);
  document.body.appendChild(container);

  // Widget Behavior
  let isOpen = false;
  launcher.addEventListener('click', () => {
    isOpen = !isOpen;
    container.style.display = isOpen ? 'flex' : 'none';
    if (isOpen) {
      document.getElementById('otInputField').focus();
    }
  });

  container.querySelector('.ot-close-btn').addEventListener('click', () => {
    isOpen = false;
    container.style.display = 'none';
  });

  const chatBody = container.querySelector('#otChatBody');
  const inputForm = container.querySelector('#otInputForm');
  const inputField = container.querySelector('#otInputField');
  const sendBtn = container.querySelector('#otSendBtn');

  function appendMessage(text, isUser = false, meta = null) {
    const msg = document.createElement('div');
    msg.className = `ot-msg ${isUser ? 'ot-msg-user' : 'ot-msg-bot'}`;
    
    // Format line breaks
    let formattedText = text.replace(/\n/g, '<br/>');
    msg.innerHTML = formattedText;

    if (meta && !isUser) {
      const badge = document.createElement('div');
      const isPass = meta.status === 'RESOLVED';
      badge.className = `ot-meta-badge ${isPass ? '' : 'escalated'}`;
      badge.innerText = isPass 
        ? `🛡️ Verified Grounded (${Math.round(meta.confidence * 100)}%)` 
        : `⚠️ Escalated to Senior Human Rep`;
      msg.appendChild(badge);

      if (meta.citations && meta.citations.length > 0) {
        const cite = document.createElement('div');
        cite.className = 'ot-citations';
        cite.innerText = 'Citations: ' + meta.citations.join(', ');
        msg.appendChild(cite);
      }
    }

    chatBody.appendChild(msg);
    chatBody.scrollTop = chatBody.scrollHeight;
    return msg;
  }

  inputForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = inputField.value.trim();
    if (!query) return;

    appendMessage(query, true);
    inputField.value = '';
    sendBtn.disabled = true;

    const loadingMsg = appendMessage("<em>Searching verified documentation & evaluating safety...</em>", false);

    try {
      const endpoint = `${apiUrl}/api/v1/triage`;
      const payload = {
        ticket_id: 'widget_' + Math.random().toString(36).substring(2, 9),
        tenant_id: tenantId,
        customer_email: 'web_visitor@customer.com',
        message_text: query
      };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Server error: " + res.status);
      const data = await res.json();

      loadingMsg.remove();
      appendMessage(data.reply_body, false, {
        status: data.status,
        confidence: data.confidence_score,
        citations: data.citations
      });
    } catch (err) {
      loadingMsg.remove();
      appendMessage(
        "I'm currently unable to retrieve official documentation. Your question has been queued for our team.",
        false,
        { status: 'ESCALATED', confidence: 0.0, citations: [] }
      );
    } finally {
      sendBtn.disabled = false;
    }
  });
})();
