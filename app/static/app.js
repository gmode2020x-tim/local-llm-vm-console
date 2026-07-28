const state = {
  config: null,
  models: [],
  messages: [],
  jobs: [],
  refreshTimer: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function text(value) {
  return String(value ?? "").trim();
}

function escapeHtml(value) {
  return text(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let value = Number(bytes);
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") return "-";
  return `${Number(value).toFixed(1)}%`;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: options.body instanceof FormData ? {} : { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || payload.detail || `HTTP ${response.status}`);
  }
  return payload;
}

function setStatus(ok, message) {
  const status = $("#status");
  status.textContent = message;
  status.className = `status ${ok ? "ok" : "error"}`;
}

function setOptions(select, items, selected, labeler = (item) => item) {
  const current = selected ?? select.value;
  select.innerHTML = "";
  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = typeof item === "string" ? item : item.value;
    option.textContent = labeler(item);
    select.appendChild(option);
  });
  if (current) select.value = current;
}

function renderRuntimeFacts() {
  const rows = [
    ["Ollama", state.config?.ollama_base_url || "-"],
    ["OpenAI API", state.config?.openai_base_url || "-"],
    ["Host worker", state.config?.host_worker_status_url || "-"],
    ["Default model", state.config?.default_model || "-"],
    ["Active profile", state.config?.active_profile || "-"],
    ["Refresh", `${state.config?.monitoring?.refresh_seconds || 5}s`],
  ];
  $("#runtimeFacts").innerHTML = rows.map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join("");
}

function renderModels() {
  const modelNames = state.models.map((model) => model.name);
  if (state.config?.default_model && !modelNames.includes(state.config.default_model)) {
    modelNames.unshift(state.config.default_model);
  }
  setOptions($("#globalModel"), modelNames, state.config?.default_model);
  $("#modelCount").textContent = state.models.length.toLocaleString();
  $("#activeModelState").textContent = $("#globalModel").value || "not selected";
  $("#modelsTable").innerHTML = state.models.map((model) => `
    <tr>
      <td><strong>${escapeHtml(model.name)}</strong><br><small>${escapeHtml(model.modified_at || "")}</small></td>
      <td>${escapeHtml(model.source || "-")}</td>
      <td>${escapeHtml(model.family || "-")}</td>
      <td>${escapeHtml(model.parameter_size || "-")}</td>
      <td>${escapeHtml(model.quantization || "-")}</td>
      <td>${formatBytes(model.size)}</td>
    </tr>
  `).join("") || `<tr><td colspan="6" class="empty">No models reported by the configured endpoint.</td></tr>`;
}

function renderProfiles() {
  const profiles = state.config?.profiles || {};
  const names = Object.keys(profiles);
  setOptions($("#globalProfile"), names, state.config?.active_profile);
  $("#profileGrid").innerHTML = names.map((name) => {
    const profile = profiles[name];
    return `
      <article class="profile-card" data-profile="${escapeHtml(name)}">
        <strong>${escapeHtml(name)}</strong>
        <label>Temperature<input data-field="temperature" type="number" min="0" max="2" step="0.05" value="${profile.temperature}"></label>
        <label>Top P<input data-field="top_p" type="number" min="0" max="1" step="0.05" value="${profile.top_p}"></label>
        <label>Max Tokens<input data-field="max_tokens" type="number" min="64" max="8192" step="64" value="${profile.max_tokens}"></label>
      </article>
    `;
  }).join("");
  applyProfileInputs();
}

function applyProfileInputs() {
  const profile = state.config?.profiles?.[$("#globalProfile").value] || {};
  $("#temperature").value = profile.temperature ?? 0.25;
  $("#topP").value = profile.top_p ?? 0.9;
  $("#maxTokens").value = profile.max_tokens ?? 700;
}

function renderConfig() {
  $("#ollamaUrl").value = state.config?.ollama_base_url || "";
  $("#openaiUrl").value = state.config?.openai_base_url || "";
  $("#hostWorkerUrl").value = state.config?.host_worker_status_url || "";
  $("#defaultModel").value = state.config?.default_model || "";
  $("#refreshSeconds").value = state.config?.monitoring?.refresh_seconds || 5;
  $("#processFilters").value = (state.config?.monitoring?.process_filters || []).join(", ");
  renderRuntimeFacts();
  renderProfiles();
}

function renderMetrics(metrics) {
  $("#cpuMetric").textContent = formatPercent(metrics.cpu_percent);
  $("#memoryMetric").textContent = formatPercent(metrics.memory?.percent);
  const gpus = metrics.gpu || [];
  $("#gpuState").textContent = gpus.length ? `${gpus.length} GPU(s)` : "none";
  $("#gpuList").innerHTML = gpus.map((gpu) => `
    <article class="card">
      <strong>${escapeHtml(gpu.name || "GPU")}</strong>
      <small>GPU ${gpu.index ?? "-"} | ${escapeHtml(gpu.source || "metrics")}</small>
      <span>Utilization: ${formatPercent(gpu.utilization_percent)}</span>
      <span>VRAM: ${gpu.memory_used_mb ?? "-"} / ${gpu.memory_total_mb ?? "-"} MB</span>
      <span>Free: ${gpu.memory_free_mb ?? "-"} MB</span>
      <span>Temperature: ${gpu.temperature_c ?? "-"} C</span>
      ${gpu.driver_version ? `<small>Driver: ${escapeHtml(gpu.driver_version)}</small>` : ""}
    </article>
  `).join("") || `<div class="empty">No GPU metrics available. Configure the host worker or install NVIDIA drivers on the machine that owns the GPU.</div>`;

  $("#processTable").innerHTML = (metrics.processes || []).map((proc) => `
    <tr>
      <td>${proc.pid}</td>
      <td><strong>${escapeHtml(proc.name || "-")}</strong><br><small>${escapeHtml(proc.status || "")}</small></td>
      <td>${formatPercent(proc.cpu_percent)}</td>
      <td>${proc.memory_mb ?? "-"} MB</td>
    </tr>
  `).join("") || `<tr><td colspan="4" class="empty">No matching LLM processes found.</td></tr>`;
  $("#processState").textContent = `${(metrics.processes || []).length} shown`;
}

function renderConversation() {
  const container = $("#conversation");
  container.innerHTML = state.messages.map((message) => `
    <article class="message ${message.role}">
      <strong>${escapeHtml(message.role)}</strong>
      <span>${escapeHtml(message.content)}</span>
    </article>
  `).join("");
  container.scrollTop = container.scrollHeight;
}

function renderChatMetrics(result = {}) {
  const usage = result.usage || {};
  const rows = [
    ["Model", result.model || $("#globalModel").value || "-"],
    ["Profile", result.profile || $("#globalProfile").value || "-"],
    ["Elapsed", result.elapsed_ms ? `${result.elapsed_ms} ms` : "-"],
    ["Finish", result.finish_reason || "-"],
    ["Prompt tokens", usage.prompt_tokens ?? "-"],
    ["Completion tokens", usage.completion_tokens ?? "-"],
  ];
  $("#chatMetrics").innerHTML = rows.map(([key, value]) => `<dt>${key}</dt><dd>${value}</dd>`).join("");
  $("#responseState").textContent = result.elapsed_ms ? `${result.elapsed_ms} ms` : "no response";
}

async function loadStatus() {
  const payload = await requestJson("api/status");
  state.config = payload.state;
  state.models = payload.models || [];
  state.jobs = payload.jobs || [];
  setStatus(payload.models_ok, payload.models_ok ? `${state.models.length} model(s) reachable` : payload.model_error || "LLM endpoint unreachable");
  $("#endpointMetric").textContent = payload.models_ok ? "Online" : "Down";
  $("#runtimeState").textContent = payload.models_ok ? "ready" : "review";
  renderModels();
  renderConfig();
  renderMetrics(payload.metrics);
  await loadLogsList();
  scheduleRefresh();
}

function scheduleRefresh() {
  if (state.refreshTimer) clearInterval(state.refreshTimer);
  const seconds = Number(state.config?.monitoring?.refresh_seconds || 5);
  state.refreshTimer = setInterval(refreshLightweight, Math.max(2, seconds) * 1000);
}

async function refreshLightweight() {
  try {
    const payload = await requestJson("api/metrics");
    renderMetrics(payload.metrics);
  } catch (error) {
    setStatus(false, error.message);
  }
}

async function sendChat(event) {
  event.preventDefault();
  const prompt = text($("#promptInput").value);
  if (!prompt) return;
  $("#sendButton").disabled = true;
  $("#chatState").textContent = "generating";
  state.messages.push({ role: "user", content: prompt });
  $("#promptInput").value = "";
  renderConversation();
  try {
    const payload = await requestJson("api/chat", {
      method: "POST",
      body: JSON.stringify({
        model: $("#globalModel").value,
        profile: $("#globalProfile").value,
        system_prompt: $("#systemPrompt").value,
        temperature: Number($("#temperature").value),
        top_p: Number($("#topP").value),
        max_tokens: Number($("#maxTokens").value),
        messages: state.messages,
      }),
    });
    state.messages.push({ role: "assistant", content: payload.response });
    renderConversation();
    renderChatMetrics(payload);
    $("#chatState").textContent = "complete";
  } catch (error) {
    state.messages.push({ role: "assistant", content: `Error: ${error.message}` });
    renderConversation();
    setStatus(false, error.message);
    $("#chatState").textContent = "error";
  } finally {
    $("#sendButton").disabled = false;
  }
}

async function saveConfig(event) {
  event.preventDefault();
  const profiles = {};
  $$(".profile-card").forEach((card) => {
    const name = card.dataset.profile;
    profiles[name] = {
      temperature: Number(card.querySelector('[data-field="temperature"]').value),
      top_p: Number(card.querySelector('[data-field="top_p"]').value),
      max_tokens: Number(card.querySelector('[data-field="max_tokens"]').value),
    };
  });
  const payload = await requestJson("api/config", {
    method: "POST",
    body: JSON.stringify({
      ollama_base_url: $("#ollamaUrl").value,
      openai_base_url: $("#openaiUrl").value,
      host_worker_status_url: $("#hostWorkerUrl").value,
      default_model: $("#defaultModel").value,
      active_profile: $("#globalProfile").value,
      profiles,
      monitoring: {
        refresh_seconds: Number($("#refreshSeconds").value || 5),
        process_filters: $("#processFilters").value.split(",").map(text).filter(Boolean),
      },
    }),
  });
  state.config = payload.state;
  setStatus(true, "Settings saved");
  $("#configState").textContent = "saved";
  await loadStatus();
}

async function pullModel(event) {
  event.preventDefault();
  const model = text($("#pullModel").value);
  if (!model) return;
  const payload = await requestJson("api/models/pull", {
    method: "POST",
    body: JSON.stringify({ model }),
  });
  $("#pullModel").value = "";
  setStatus(payload.ok, payload.job.message || `Pull job: ${payload.job.id}`);
  await loadStatus();
}

async function loadLogsList() {
  const payload = await requestJson("api/logs");
  setOptions($("#logSelect"), payload.logs || [], $("#logSelect").value);
}

async function loadSelectedLog() {
  const name = $("#logSelect").value;
  if (!name) {
    $("#logOutput").textContent = "";
    return;
  }
  const payload = await requestJson(`api/logs/${encodeURIComponent(name)}?lines=220`);
  $("#logOutput").textContent = (payload.lines || []).join("");
}

function bindTabs() {
  $$("[data-tab-target]").forEach((button) => {
    button.addEventListener("click", () => {
      $$("[data-tab-target]").forEach((item) => item.classList.toggle("active", item === button));
      $$("[data-tab-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.tabPanel === button.dataset.tabTarget));
    });
  });
}

function bindEvents() {
  bindTabs();
  $("#refreshButton").addEventListener("click", loadStatus);
  $("#globalProfile").addEventListener("change", applyProfileInputs);
  $("#chatForm").addEventListener("submit", sendChat);
  $("#clearConversation").addEventListener("click", () => {
    state.messages = [];
    renderConversation();
    renderChatMetrics();
  });
  $("#configForm").addEventListener("submit", saveConfig);
  $("#pullForm").addEventListener("submit", pullModel);
  $("#loadLogButton").addEventListener("click", loadSelectedLog);
}

bindEvents();
renderChatMetrics();
loadStatus().catch((error) => setStatus(false, error.message));
