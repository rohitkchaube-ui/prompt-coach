// Prompt Coach frontend: plain JavaScript, no build step.

const $ = (id) => document.getElementById(id);
let current = null; // { original, report }
let models = []; // [{ id, label, input, output, best_for }]

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? "Please enter a prompt." : data.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

function setStatus(text, isError = false) {
  $("status").textContent = text;
  $("status").classList.toggle("error", isError);
}

function scoreColor(score10) {
  if (score10 >= 8) return "var(--good)";
  if (score10 >= 5) return "var(--mid)";
  return "var(--bad)";
}

const modelLabel = (id) => (models.find((m) => m.id === id) || {}).label || id;

// "2026-11-22T12:47:17+00:00" -> "Nov 22, 12:47 PM" in the viewer's local time.
function formatDate(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function formatCost(usd) {
  if (usd === 0) return "$0";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(3)}`;
}

// Shows "Claude Opus 5.5 · 1,234 in · 567 out · $0.0153" above a response.
function renderUsage(el, usage, prefix = "") {
  if (!usage) {
    el.replaceChildren();
    return;
  }
  const n = (x) => x.toLocaleString();
  el.innerHTML = `
    <span>${prefix}<b></b></span>
    <span><b>${n(usage.input_tokens)}</b> input tokens</span>
    <span><b>${n(usage.output_tokens)}</b> output tokens</span>
    <span>Cost <b>${formatCost(usage.cost_usd)}</b></span>`;
  el.querySelector("span b").textContent = modelLabel(usage.model);
}

function renderModelPicker(recommended) {
  $("model-select").replaceChildren(
    ...models.map((m) => {
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent =
        `${m.label} · $${m.input} in / $${m.output} out per 1M tokens` +
        (m.id === recommended ? " (recommended)" : "");
      return opt;
    })
  );
  if (recommended) $("model-select").value = recommended;
}

function renderReport(original, report, usage) {
  current = { original, report };
  $("report").hidden = false;
  $("compare").hidden = true;
  $("compare-total").hidden = true;
  renderUsage($("coach-usage"), usage, "Coaching by ");

  // Sessions saved before this feature have no recommendation.
  const rec = report.recommended_model;
  $("rec-model").textContent = rec ? modelLabel(rec) : "No recommendation for this older session";
  $("rec-reason").textContent = report.recommendation_reason || "";
  renderModelPicker(rec);
  $("overall").textContent = report.overall_score;
  $("summary").textContent = report.summary;
  $("improved").textContent = report.improved_prompt;

  $("criteria").replaceChildren(
    ...report.criteria.map((c) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <div class="head"><span></span><span>${c.score}/10</span></div>
        <div class="bar"><span style="width:${c.score * 10}%;background:${scoreColor(c.score)}"></span></div>
        <p></p>`;
      li.querySelector(".head span").textContent = c.name;
      li.querySelector("p").textContent = c.feedback;
      return li;
    })
  );

  $("changes").replaceChildren(
    ...report.key_changes.map((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      return li;
    })
  );
}

async function coach() {
  const prompt = $("prompt").value.trim();
  if (!prompt) return setStatus("Type a prompt first.", true);
  $("coach-btn").disabled = true;
  setStatus("Claude is reviewing your prompt...");
  try {
    const { report, usage } = await api("/api/coach", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    });
    renderReport(prompt, report, usage);
    setStatus("");
    loadHistory();
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    $("coach-btn").disabled = false;
  }
}

async function compare() {
  if (!current) return;
  $("compare-btn").disabled = true;
  const model = $("model-select").value;
  setStatus(`Running both prompts on ${modelLabel(model)}...`);
  try {
    const out = await api("/api/compare", {
      method: "POST",
      body: JSON.stringify({
        original: current.original,
        improved: current.report.improved_prompt,
        model,
      }),
    });
    for (const side of ["original", "improved"]) {
      renderUsage($(`usage-${side}`), out[side].usage);
      $(`out-${side}`).textContent = out[side].text;
    }
    const total = out.original.usage.cost_usd + out.improved.usage.cost_usd;
    $("compare-total").innerHTML = `<span>Comparison total: <b>${formatCost(total)}</b></span>`;
    $("compare-total").hidden = false;
    $("compare").hidden = false;
    setStatus("");
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    $("compare-btn").disabled = false;
  }
}

async function loadHistory() {
  const sessions = await api("/api/history").catch(() => []);
  $("history-empty").hidden = sessions.length > 0;
  $("history-list").replaceChildren(
    ...sessions.map((s) => {
      const li = document.createElement("li");
      li.title = s.original_prompt;
      li.innerHTML = `
        <div class="hist-meta">
          <span class="pill"></span>
          <span class="hist-date"></span>
          <button class="del" title="Delete" aria-label="Delete this session">✕</button>
        </div>
        <p class="hist-text"></p>`;
      const pill = li.querySelector(".pill");
      pill.textContent = s.overall_score;
      pill.style.color = scoreColor(s.overall_score / 10);
      li.querySelector(".hist-date").textContent = formatDate(s.created_at);
      li.querySelector(".hist-text").textContent = s.original_prompt;
      li.addEventListener("click", () => {
        $("prompt").value = s.original_prompt;
        renderReport(s.original_prompt, s.report, s.usage);
      });
      li.querySelector(".del").addEventListener("click", async (e) => {
        e.stopPropagation();
        await api(`/api/history/${s.id}`, { method: "DELETE" }).catch(() => {});
        loadHistory();
      });
      return li;
    })
  );
}

$("coach-btn").addEventListener("click", coach);
$("compare-btn").addEventListener("click", compare);
$("copy-btn").addEventListener("click", async () => {
  await navigator.clipboard.writeText($("improved").textContent);
  $("copy-btn").textContent = "Copied!";
  setTimeout(() => ($("copy-btn").textContent = "Copy"), 1500);
});
$("prompt").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) coach();
});

api("/api/models")
  .then((list) => (models = list))
  .catch(() => {})
  .finally(loadHistory);
