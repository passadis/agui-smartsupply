const statusEl = document.getElementById('status');
const messagesEl = document.getElementById('messages');
const eventsEl = document.getElementById('events');
const toolsEl = document.getElementById('tools');
const runIdEl = document.getElementById('runId');
const runStateEl = document.getElementById('runState');

const composer = document.getElementById('composer');
const promptEl = document.getElementById('prompt');
const threadEl = document.getElementById('threadId');
const sendBtn = document.getElementById('send');

let currentAssistantBubble = null;
let toolCards = new Map();
let lastStep = null;
let approvalCards = new Map();

function normalizeApprovalDecision(text) {
  const t = (text || '').trim().toLowerCase();
  if (!t) return null;

  if (['y', 'yes', 'yeah', 'yep', 'approve', 'approved', 'ok', 'okay', 'sure', 'proceed'].includes(t)) {
    return true;
  }

  if (['n', 'no', 'nope', 'reject', 'rejected', 'cancel', 'stop'].includes(t)) {
    return false;
  }

  return null;
}

function getMostRecentPendingApproval() {
  let best = null;
  for (const [_id, card] of approvalCards.entries()) {
    if (!card) continue;
    if (card.approve?.disabled || card.reject?.disabled) continue;
    if (!card.sendDecision) continue;
    if (!best || (card.createdAt || 0) > (best.createdAt || 0)) best = card;
  }
  return best;
}

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.classList.remove('ok', 'bad');
  if (cls) statusEl.classList.add(cls);
}

function appendBubble(role, text, kind) {
  const div = document.createElement('div');
  div.className = `bubble ${role} ${kind || ''}`.trim();
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function appendImageCard(url, alt) {
  const wrap = document.createElement('div');
  wrap.className = 'bubble assistant';

  const img = document.createElement('img');
  img.className = 'imgCard';
  img.src = url;
  img.alt = alt || 'image';
  img.loading = 'lazy';

  const cap = document.createElement('div');
  cap.className = 'imgCaption';
  cap.textContent = alt ? `${alt}` : url;

  wrap.appendChild(img);
  wrap.appendChild(cap);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function safeJson(obj) {
  try { return JSON.stringify(obj, null, 2); } catch { return String(obj); }
}

function looksLikeImageUrl(value) {
  if (!value || typeof value !== 'string') return false;
  const v = value.toLowerCase().split('?')[0].split('#')[0];
  return (v.startsWith('http://') || v.startsWith('https://')) &&
         (v.endsWith('.png') || v.endsWith('.jpg') || v.endsWith('.jpeg') || v.endsWith('.gif') || v.endsWith('.webp') || v.endsWith('.svg'));
}

function appendApprovalCard(payload) {
  const approvalId = payload.approvalId;
  if (!approvalId) return;

  // Avoid duplicates if server retries
  if (approvalCards.has(approvalId)) return;

  const wrap = document.createElement('div');
  wrap.className = 'bubble assistant approvalWrap';

  const card = document.createElement('div');
  card.className = 'approvalCard';

  const head = document.createElement('div');
  head.className = 'approvalHead';

  const icon = document.createElement('div');
  icon.className = 'approvalIcon';
  icon.innerHTML = `
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2l7 4v6c0 5-3 9-7 10-4-1-7-5-7-10V6l7-4z" stroke="rgba(10,16,32,0.9)" stroke-width="1.6" />
      <path d="M8.6 12.2l2.2 2.2 4.8-5" stroke="rgba(10,16,32,0.9)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    </svg>`;

  const titles = document.createElement('div');
  titles.className = 'approvalTitles';

  const title = document.createElement('div');
  title.className = 'approvalTitle';
  title.textContent = payload.title || 'Confirmation required';

  const sub = document.createElement('div');
  sub.className = 'approvalSub';
  sub.textContent = payload.description || (payload.toolName ? `Tool: ${payload.toolName}` : '');

  titles.appendChild(title);
  titles.appendChild(sub);

  head.appendChild(icon);
  head.appendChild(titles);

  const body = document.createElement('div');
  body.className = 'approvalBody';

  const toolLine = document.createElement('div');
  toolLine.className = 'approvalMeta';
  toolLine.textContent = payload.toolName ? `Action: ${payload.toolName}` : 'Action: (unknown)';

  const args = document.createElement('pre');
  args.className = 'approvalArgs';
  args.textContent = safeJson(payload.arguments || {});

  body.appendChild(toolLine);

  const previewUrl = payload.previewImageUrl;
  if (looksLikeImageUrl(previewUrl)) {
    const img = document.createElement('img');
    img.className = 'approvalPreview';
    img.src = previewUrl;
    img.alt = 'preview';
    img.loading = 'lazy';
    body.appendChild(img);

    const cap = document.createElement('div');
    cap.className = 'approvalHint';
    cap.textContent = 'Preview (the URL you are about to save)';
    body.appendChild(cap);
  }

  body.appendChild(args);

  const actions = document.createElement('div');
  actions.className = 'approvalActions';

  const approve = document.createElement('button');
  approve.type = 'button';
  approve.className = 'approvalBtn approve';
  approve.textContent = 'Approve';

  const reject = document.createElement('button');
  reject.type = 'button';
  reject.className = 'approvalBtn reject';
  reject.textContent = 'Reject';

  const status = document.createElement('div');
  status.className = 'approvalStatus';
  status.textContent = 'Waiting for your decision…';

  async function sendDecision(approved) {
    approve.disabled = true;
    reject.disabled = true;
    status.textContent = approved ? 'Approved — applying change…' : 'Rejected — change cancelled.';
    try {
      const res = await fetch('/agui/approval', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ approvalId, approved })
      });
      if (!res.ok) {
        status.textContent = `Decision sent, but server replied HTTP ${res.status}`;
      }
    } catch (e) {
      status.textContent = `Failed to send decision: ${String(e)}`;
    }
  }

  approve.addEventListener('click', () => sendDecision(true));
  reject.addEventListener('click', () => sendDecision(false));

  actions.appendChild(approve);
  actions.appendChild(reject);
  actions.appendChild(status);

  card.appendChild(head);
  card.appendChild(body);
  card.appendChild(actions);

  wrap.appendChild(card);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  approvalCards.set(approvalId, { wrap, status, approve, reject, sendDecision, createdAt: Date.now() });
}

function appendEventLine(obj) {
  const line = document.createElement('div');
  line.className = 'eventLine';
  line.textContent = JSON.stringify(obj);
  eventsEl.appendChild(line);
  eventsEl.scrollTop = eventsEl.scrollHeight;
}

function ensureToolCard(toolCallId, toolCallName) {
  if (toolCards.has(toolCallId)) return toolCards.get(toolCallId);

  const card = document.createElement('div');
  card.className = 'tool';

  const head = document.createElement('div');
  head.className = 'toolHead';

  const name = document.createElement('div');
  name.className = 'toolName';
  name.textContent = toolCallName || '(tool)';

  const state = document.createElement('div');
  state.className = 'toolState';
  state.textContent = 'starting…';

  head.appendChild(name);
  head.appendChild(state);

  const body = document.createElement('div');
  body.className = 'toolBody';
  body.textContent = '';

  card.appendChild(head);
  card.appendChild(body);

  toolsEl.prepend(card);
  toolCards.set(toolCallId, { card, name, state, body });
  return toolCards.get(toolCallId);
}

function onAgUiEvent(evt) {
  appendEventLine(evt);

  switch (evt.type) {
    case 'RunStarted':
      setStatus('Streaming…', 'ok');
      runIdEl.textContent = evt.runId || '—';
      runStateEl.textContent = 'running';
      lastStep = null;
      break;

    case 'RunFinished':
      setStatus('Idle', 'ok');
      runStateEl.textContent = 'finished';
      if (lastStep) runStateEl.textContent = `finished (${lastStep})`;
      break;

    case 'RunError':
      setStatus('Error', 'bad');
      runStateEl.textContent = 'error';
      appendBubble('assistant', evt.message || 'RunError', 'error');
      break;

    case 'StepStarted':
      lastStep = evt.stepName || null;
      runStateEl.textContent = lastStep ? `running (${lastStep})` : 'running';
      break;

    case 'StepFinished':
      lastStep = evt.stepName || lastStep;
      runStateEl.textContent = lastStep ? `running (${lastStep})` : 'running';
      break;

    case 'TextMessageStart':
      currentAssistantBubble = appendBubble('assistant', '');
      break;

    case 'TextMessageContent':
      if (!currentAssistantBubble) currentAssistantBubble = appendBubble('assistant', '');
      currentAssistantBubble.textContent += evt.delta || '';
      messagesEl.scrollTop = messagesEl.scrollHeight;
      break;

    case 'TextMessageEnd':
      currentAssistantBubble = null;
      break;

    case 'ToolCallStart': {
      const t = ensureToolCard(evt.toolCallId, evt.toolCallName);
      t.state.textContent = 'args…';
      break;
    }

    case 'ToolCallArgs': {
      const t = ensureToolCard(evt.toolCallId, '(tool)');
      t.state.textContent = 'args…';
      t.body.textContent += evt.delta || '';
      break;
    }

    case 'ToolCallEnd': {
      const t = ensureToolCard(evt.toolCallId, '(tool)');
      t.state.textContent = 'running…';
      break;
    }

    case 'ToolCallResult': {
      const t = ensureToolCard(evt.toolCallId, '(tool)');
      t.state.textContent = 'done';
      t.body.textContent = `${t.body.textContent}\n\nRESULT:\n${evt.content || ''}`.trim();
      break;
    }

    case 'Custom':
      if (evt.name === 'image' && evt.value && evt.value.url) {
        appendImageCard(evt.value.url, evt.value.alt);
      } else if (evt.name === 'approval_request' && evt.value) {
        appendApprovalCard(evt.value);
      } else if (evt.name === 'approval_result' && evt.value && evt.value.approvalId) {
        const card = approvalCards.get(evt.value.approvalId);
        if (card) {
          if (evt.value.reason === 'timeout') {
            card.status.textContent = 'Timed out — change cancelled.';
          } else {
            card.status.textContent = evt.value.approved ? 'Approved.' : 'Rejected.';
          }
          card.approve.disabled = true;
          card.reject.disabled = true;
        }
      }
      break;

    default:
      break;
  }
}

function parseSseChunk(buffer) {
  // Minimal SSE parser for our server output: blocks separated by \n\n, data lines with JSON.
  const events = [];
  while (true) {
    const idx = buffer.indexOf('\n\n');
    if (idx === -1) break;

    const block = buffer.slice(0, idx);
    buffer = buffer.slice(idx + 2);

    const lines = block.split('\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const jsonStr = line.slice(6);
        try {
          events.push(JSON.parse(jsonStr));
        } catch {
          // ignore malformed partials
        }
      }
    }
  }
  return { events, buffer };
}

async function streamAgUi(threadId, message) {
  toolCards.clear();
  toolsEl.innerHTML = '';
  approvalCards.clear();

  const res = await fetch('/agui', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ threadId, message })
  });

  if (!res.ok || !res.body) {
    setStatus(`HTTP ${res.status}`, 'bad');
    const t = await res.text();
    appendBubble('assistant', t || `Request failed: ${res.status}`, 'error');
    return;
  }

  setStatus('Connected', 'ok');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const out = parseSseChunk(buffer);
    buffer = out.buffer;
    for (const evt of out.events) onAgUiEvent(evt);
  }
}

composer.addEventListener('submit', async (e) => {
  e.preventDefault();

  const text = (promptEl.value || '').trim();
  const threadId = (threadEl.value || 'demo-thread').trim();

  if (!text) return;

  // If there's a pending approval card, allow the user to type yes/no instead of clicking.
  // This avoids starting a new agent run (which may lose context).
  const decision = normalizeApprovalDecision(text);
  const pendingApproval = decision === null ? null : getMostRecentPendingApproval();
  if (pendingApproval) {
    appendBubble('user', text);
    promptEl.value = '';

    sendBtn.disabled = true;
    setStatus('Sending decision…', 'ok');
    try {
      await pendingApproval.sendDecision(Boolean(decision));
    } catch (err) {
      setStatus('Error', 'bad');
      appendBubble('assistant', String(err), 'error');
    } finally {
      sendBtn.disabled = false;
    }
    return;
  }

  appendBubble('user', text);
  promptEl.value = '';

  sendBtn.disabled = true;
  setStatus('Sending…', 'ok');

  try {
    await streamAgUi(threadId, text);
  } catch (err) {
    setStatus('Error', 'bad');
    appendBubble('assistant', String(err), 'error');
  } finally {
    sendBtn.disabled = false;
  }
});

setStatus('Idle', 'ok');
