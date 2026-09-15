const state = {
  config: null,
  session: null,
  turns: [],
  sending: false,
};

const els = {};

const icons = {
  pulse: '<svg viewBox="0 0 24 24"><path d="M4 12h3l2-6 4 12 2-6h5"/></svg>',
  laptop: '<svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="11" rx="2"/><path d="M2 19h20"/></svg>',
  book: '<svg viewBox="0 0 24 24"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5v-16ZM20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5v-16Z"/></svg>',
  shield: '<svg viewBox="0 0 24 24"><path d="M12 3 20 6v5c0 5.2-3.4 8.8-8 10-4.6-1.2-8-4.8-8-10V6l8-3Z"/><path d="m8.5 12 2.2 2.2 4.8-4.8"/></svg>',
  ticket: '<svg viewBox="0 0 24 24"><path d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2a3 3 0 0 0 0 6v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a3 3 0 0 0 0-6V7Z"/><path d="M12 8v8"/></svg>',
  meeting: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M8 2v4M16 2v4M3 10h18M9 16h2M9 19h2"/></svg>',
  arrow: '<svg viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>',
  spark: '<svg viewBox="0 0 32 32"><path d="M16 2 19.8 12.2 30 16l-10.2 3.8L16 30l-3.8-10.2L2 16l10.2-3.8L16 2Z"/></svg>',
  trace: '<svg viewBox="0 0 20 20"><path d="M3 10h3l2-5 4 10 2-5h3"/></svg>',
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  cacheElements();
  bindEvents();
  try {
    state.config = await api("/api/config");
    renderProviderOptions();
    renderQuickActions();
    await createSession();
  } catch (error) {
    showToast(`Không thể khởi động UI: ${error.message}`, "error", 8000);
    setComposerDisabled(true);
  }
}

function cacheElements() {
  [
    "sidebar", "newConversationBtn", "mobileSidebarBtn", "providerDot", "providerLabel",
    "sidebarVersion", "artifactVersion", "downloadBtn", "settingsBtn", "conversation",
    "welcomePanel", "quickActions", "activityFeed", "activityEmpty", "toolEventCount",
    "metaProvider", "metaModel", "metaTools", "metaTranscript", "composerForm", "messageInput",
    "sendButton", "charCount", "settingsDialog", "settingsForm", "settingsCancel",
    "dialogCancelButton", "providerSelect", "providerHint", "versionInput", "modelInput",
    "historyWindow", "maxRounds", "toastRegion",
  ].forEach((id) => { els[id] = document.getElementById(id); });
}

function bindEvents() {
  els.composerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitMessage(els.messageInput.value);
  });
  els.messageInput.addEventListener("input", () => {
    autosizeComposer();
    els.charCount.textContent = `${els.messageInput.value.length}/8000`;
  });
  els.messageInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      els.composerForm.requestSubmit();
    }
  });
  document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => submitMessage(button.dataset.prompt));
  });
  els.newConversationBtn.addEventListener("click", () => createSession(true));
  els.settingsBtn.addEventListener("click", () => els.settingsDialog.showModal());
  els.settingsCancel.addEventListener("click", () => els.settingsDialog.close());
  els.dialogCancelButton.addEventListener("click", () => els.settingsDialog.close());
  els.settingsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    els.settingsDialog.close();
    await createSession(true);
  });
  els.providerSelect.addEventListener("change", updateProviderHint);
  els.downloadBtn.addEventListener("click", downloadTranscript);
  els.mobileSidebarBtn.addEventListener("click", () => els.sidebar.classList.toggle("open"));
  document.addEventListener("click", (event) => {
    if (window.innerWidth <= 920 && els.sidebar.classList.contains("open") &&
        !els.sidebar.contains(event.target) && !els.mobileSidebarBtn.contains(event.target)) {
      els.sidebar.classList.remove("open");
    }
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `HTTP ${response.status}`);
  }
  return body;
}

function renderProviderOptions() {
  els.providerSelect.replaceChildren();
  state.config.providers.forEach((provider) => {
    const option = document.createElement("option");
    option.value = provider.id;
    option.textContent = `${provider.label}${provider.ready ? " · ready" : " · thiếu key"}`;
    els.providerSelect.appendChild(option);
  });
  const readyProvider = state.config.providers.find((provider) => provider.ready);
  if (readyProvider) els.providerSelect.value = readyProvider.id;
  updateProviderHint();
}

function updateProviderHint() {
  const provider = selectedProvider();
  if (!provider) return;
  els.providerHint.textContent = provider.ready
    ? `${provider.key_env} đã được nạp an toàn · mặc định ${provider.default_model}`
    : `Chưa thấy ${provider.key_env} trong .env · UI vẫn mở được nhưng chưa gọi model.`;
  els.modelInput.placeholder = provider.default_model;
}

function selectedProvider() {
  return state.config?.providers.find((provider) => provider.id === els.providerSelect.value);
}

function renderQuickActions() {
  els.quickActions.replaceChildren();
  state.config.quick_actions.forEach((action) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-card";
    button.innerHTML = `
      <span class="quick-card-icon">${icons[action.icon] || icons.spark}</span>
      <span class="quick-card-copy"><strong></strong><span></span></span>
      ${icons.arrow}
    `;
    button.querySelector("strong").textContent = action.title;
    button.querySelector(".quick-card-copy span").textContent = action.description;
    button.addEventListener("click", () => submitMessage(action.prompt));
    els.quickActions.appendChild(button);
  });
}

async function createSession(notify = false) {
  if (!state.config) return;
  if (state.sending) return;
  setComposerDisabled(true);
  const payload = {
    provider: els.providerSelect.value || "openrouter",
    version: els.versionInput.value.trim() || "v3",
    model: els.modelInput.value.trim() || null,
    history_window: Number(els.historyWindow.value) || 5,
    max_tool_rounds: Number(els.maxRounds.value) || 4,
  };
  try {
    const body = await api("/api/sessions", { method: "POST", body: JSON.stringify(payload) });
    state.session = body.session;
    state.turns = [];
    resetConversation();
    renderSessionMeta();
    renderActivity();
    updateProviderStatus();
    if (notify) showToast("Đã tạo phiên hỗ trợ và transcript mới.", "success");
  } catch (error) {
    showToast(`Không thể tạo phiên: ${error.message}`, "error", 7000);
  } finally {
    setComposerDisabled(false);
    els.messageInput.focus();
  }
}

async function submitMessage(rawMessage) {
  const message = (rawMessage || "").trim();
  if (!message || state.sending) return;
  if (!state.session) {
    await createSession();
    if (!state.session) return;
  }
  state.sending = true;
  setComposerDisabled(true);
  els.sidebar.classList.remove("open");
  els.messageInput.value = "";
  els.charCount.textContent = "0/8000";
  autosizeComposer();
  hideWelcome();
  appendUserMessage(message);
  const typing = appendTypingIndicator();
  scrollConversation();

  try {
    const body = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ session_id: state.session.session_id, message }),
    });
    typing.remove();
    state.session = body.session;
    state.turns.push(body.turn);
    appendAssistantTurn(body.turn);
    renderActivity();
    renderSessionMeta();
    if (body.turn.status === "provider_error") {
      showToast("Provider trả lỗi — mở trace để xem chi tiết.", "error", 6500);
    } else if (body.turn.status === "blocked_sensitive_input") {
      showToast("Thông tin nhạy cảm đã được chặn và che khỏi transcript.", "error", 6500);
    }
  } catch (error) {
    typing.remove();
    appendSystemError(error.message);
    showToast(`Gửi yêu cầu thất bại: ${error.message}`, "error", 7000);
  } finally {
    state.sending = false;
    setComposerDisabled(false);
    els.messageInput.focus();
    scrollConversation();
  }
}

function resetConversation() {
  [...els.conversation.querySelectorAll(".message-row")].forEach((node) => node.remove());
  els.welcomePanel.classList.remove("hidden");
}

function hideWelcome() {
  els.welcomePanel.classList.add("hidden");
}

function appendUserMessage(message) {
  const row = document.createElement("article");
  row.className = "message-row user";
  const content = document.createElement("div");
  content.className = "message-content";
  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.innerHTML = `<span>${timeLabel()}</span><strong>Bạn</strong>`;
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = message;
  content.append(meta, bubble);
  row.appendChild(content);
  els.conversation.appendChild(row);
}

function appendTypingIndicator() {
  const row = document.createElement("article");
  row.className = "message-row assistant typing-row";
  const avatar = createAvatar();
  const content = document.createElement("div");
  content.className = "message-content";
  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.innerHTML = `<strong>Slopper</strong><span>đang phân tích yêu cầu</span>`;
  const bubble = document.createElement("div");
  bubble.className = "typing-bubble";
  bubble.innerHTML = "<span></span><span></span><span></span>";
  content.append(meta, bubble);
  row.append(avatar, content);
  els.conversation.appendChild(row);
  return row;
}

function appendInlineMarkdown(parent, text) {
  const pattern = /(\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let cursor = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      parent.appendChild(document.createTextNode(text.slice(cursor, match.index)));
    }
    const element = document.createElement(match[2] !== undefined ? "strong" : "code");
    element.textContent = match[2] ?? match[3];
    parent.appendChild(element);
    cursor = pattern.lastIndex;
  }

  if (cursor < text.length) {
    parent.appendChild(document.createTextNode(text.slice(cursor)));
  }
}

function renderMarkdown(container, markdown) {
  container.classList.add("markdown-body");
  const lines = String(markdown || "").replace(/\r\n?/g, "\n").split("\n");
  let paragraph = null;
  let list = null;
  let listType = null;

  const resetBlocks = () => {
    paragraph = null;
    list = null;
    listType = null;
  };

  for (const line of lines) {
    if (!line.trim()) {
      resetBlocks();
      continue;
    }

    const heading = line.match(/^\s*(#{1,3})\s+(.+)$/);
    if (heading) {
      resetBlocks();
      const level = Math.min(heading[1].length + 2, 5);
      const element = document.createElement(`h${level}`);
      appendInlineMarkdown(element, heading[2]);
      container.appendChild(element);
      continue;
    }

    const unordered = line.match(/^\s*[-*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      paragraph = null;
      const nextType = unordered ? "ul" : "ol";
      if (!list || listType !== nextType) {
        list = document.createElement(nextType);
        listType = nextType;
        container.appendChild(list);
      }
      const item = document.createElement("li");
      appendInlineMarkdown(item, (unordered || ordered)[1]);
      list.appendChild(item);
      continue;
    }

    list = null;
    listType = null;
    if (!paragraph) {
      paragraph = document.createElement("p");
      container.appendChild(paragraph);
    } else {
      paragraph.appendChild(document.createElement("br"));
    }
    appendInlineMarkdown(paragraph, line.trim());
  }
}

function appendAssistantTurn(turn) {
  const row = document.createElement("article");
  row.className = "message-row assistant";
  const avatar = createAvatar();
  const content = document.createElement("div");
  content.className = "message-content";
  const meta = document.createElement("div");
  meta.className = "message-meta";
  const duration = turn.duration_ms ? `${formatDuration(turn.duration_ms)}` : "";
  meta.innerHTML = `<strong>Slopper</strong><span>${duration}</span>`;

  const payload = turn.structured_response || tryParseJson(turn.assistant_text);
  const reply = payload?.reply || turn.assistant_text || "Không có phản hồi.";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  renderMarkdown(bubble, reply);
  content.append(meta, bubble);

  if (payload) {
    const chips = document.createElement("div");
    chips.className = "response-chips";
    addChip(chips, "intent", payload.intent);
    addChip(chips, "action", payload.action);
    if (Array.isArray(payload.evidence_ids) && payload.evidence_ids.length) {
      addChip(chips, "evidence", `${payload.evidence_ids.length} nguồn`);
    }
    content.appendChild(chips);
  }

  const toolEvents = turn.tool_events || [];
  if (toolEvents.length || turn.error || payload) {
    content.appendChild(createTraceDetails(turn));
  }
  row.append(avatar, content);
  els.conversation.appendChild(row);
}

function appendSystemError(message) {
  appendAssistantTurn({
    assistant_text: `UI gặp lỗi khi xử lý yêu cầu. ${message}`,
    status: "ui_error",
    error: message,
    rounds: [],
    tool_events: [],
  });
}

function createAvatar() {
  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.innerHTML = icons.spark;
  return avatar;
}

function addChip(container, label, value) {
  if (value === undefined || value === null || value === "") return;
  const chip = document.createElement("span");
  chip.className = "response-chip";
  const key = document.createElement("b");
  key.textContent = label;
  chip.append(key, document.createTextNode(String(value)));
  container.appendChild(chip);
}

function createTraceDetails(turn) {
  const details = document.createElement("details");
  details.className = "trace-group";
  const summary = document.createElement("summary");
  summary.className = "trace-summary";
  const count = (turn.tool_events || []).length;
  summary.innerHTML = `${icons.trace}<span>${count ? `${count} tool call${count > 1 ? "s" : ""}` : "Structured trace"}</span>`;
  const body = document.createElement("div");
  body.className = "trace-details";
  const pre = document.createElement("pre");
  pre.textContent = JSON.stringify({
    status: turn.status,
    rounds: turn.rounds || [],
    error: turn.error || null,
    structured_response: turn.structured_response || null,
  }, null, 2);
  body.appendChild(pre);
  details.append(summary, body);
  return details;
}

function renderActivity() {
  els.activityFeed.replaceChildren();
  const events = [];
  state.turns.forEach((turn) => {
    (turn.tool_events || []).forEach((event) => events.push({ ...event, turn_index: turn.turn_index }));
  });
  els.toolEventCount.textContent = String(events.length);
  if (!events.length) {
    const empty = document.createElement("div");
    empty.className = "empty-activity";
    empty.innerHTML = `
      <div class="radar"><span></span><span></span><span></span></div>
      <strong>Chưa có tool call</strong>
      <p>Mỗi hành động của agent sẽ xuất hiện ở đây cùng input và kết quả.</p>`;
    els.activityFeed.appendChild(empty);
    return;
  }
  events.slice().reverse().forEach((event) => els.activityFeed.appendChild(createActivityItem(event)));
}

function createActivityItem(event) {
  const [stateName, label] = toolEventState(event);
  const item = document.createElement("article");
  item.className = `activity-item ${stateName}`;
  const node = document.createElement("span");
  node.className = "activity-node";
  const card = document.createElement("div");
  card.className = "activity-card";
  const head = document.createElement("div");
  head.className = "activity-card-head";
  const name = document.createElement("span");
  name.className = "tool-name";
  name.textContent = event.tool || "unknown_tool";
  const badge = document.createElement("span");
  badge.className = "tool-state";
  badge.textContent = label;
  head.append(name, badge);

  const args = document.createElement("details");
  const argsSummary = document.createElement("summary");
  argsSummary.textContent = `Turn ${event.turn_index} · Input`;
  const argsPre = document.createElement("pre");
  argsPre.textContent = JSON.stringify(event.args || {}, null, 2);
  args.append(argsSummary, argsPre);

  const result = document.createElement("details");
  const resultSummary = document.createElement("summary");
  resultSummary.textContent = "Result / error";
  const resultPre = document.createElement("pre");
  resultPre.textContent = JSON.stringify(event.result ?? null, null, 2);
  result.append(resultSummary, resultPre);
  card.append(head, args, result);
  item.append(node, card);
  return item;
}

function toolEventState(event) {
  const result = event.result;
  if (result && typeof result === "object") {
    if (result.error) return ["error", "Lỗi"];
    if (result.awaiting_user) return ["waiting", "Cần tin"];
    if (result.status === "needs_confirmation") return ["waiting", "Xác nhận"];
  }
  return ["success", "Hoàn tất"];
}

function renderSessionMeta() {
  if (!state.session) return;
  els.artifactVersion.textContent = state.session.artifact_version;
  els.artifactVersion.title = `Prompt: ${state.session.prompt_hash}\nTools: ${state.session.tools_hash}`;
  els.sidebarVersion.textContent = state.session.version;
  els.metaProvider.textContent = state.session.provider;
  els.metaModel.textContent = state.session.model;
  els.metaTools.textContent = `${state.config.tool_count} available`;
  els.metaTranscript.textContent = state.session.transcript_path;
  els.metaTranscript.title = state.session.transcript_path;
}

function updateProviderStatus() {
  const provider = selectedProvider();
  if (!provider) return;
  els.providerDot.classList.toggle("offline", !provider.ready);
  els.providerLabel.textContent = provider.ready ? `${provider.label} ready` : `${provider.label} thiếu key`;
}

async function downloadTranscript() {
  if (!state.session) return;
  try {
    const response = await fetch(`/api/sessions/${encodeURIComponent(state.session.session_id)}/transcript`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${state.session.session_id}.transcript.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    showToast("Transcript đã được tải xuống.", "success");
  } catch (error) {
    showToast(`Không thể tải transcript: ${error.message}`, "error");
  }
}

function setComposerDisabled(disabled) {
  els.messageInput.disabled = disabled;
  els.sendButton.disabled = disabled;
}

function autosizeComposer() {
  els.messageInput.style.height = "auto";
  els.messageInput.style.height = `${Math.min(els.messageInput.scrollHeight, 140)}px`;
}

function scrollConversation() {
  requestAnimationFrame(() => {
    els.conversation.scrollTop = els.conversation.scrollHeight;
  });
}

function tryParseJson(text) {
  if (!text) return null;
  let candidate = String(text).trim();
  const embedded = candidate.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/i);
  if (embedded) {
    candidate = embedded[1];
  } else if (candidate.startsWith("```")) {
    candidate = candidate.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  }
  try {
    const parsed = JSON.parse(candidate);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function formatDuration(milliseconds) {
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `${(milliseconds / 1000).toFixed(1)} s`;
}

function timeLabel() {
  return new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit" }).format(new Date());
}

function showToast(message, type = "default", duration = 4200) {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  els.toastRegion.appendChild(toast);
  window.setTimeout(() => toast.remove(), duration);
}
