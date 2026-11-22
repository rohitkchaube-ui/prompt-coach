// Prompt Coach frontend: plain JavaScript, no build step.

const $ = (id) => document.getElementById(id);
let current = null; // { original, report }

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

function renderReport(original, report) {
  current = { original, report };
  $("report").hidden = false;
  $("compare").hidden = true;
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
    const { report } = await api("/api/coach", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    });
    renderReport(prompt, report);
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
  setStatus("Running both prompts...");
  try {
    const out = await api("/api/compare", {
      method: "POST",
      body: JSON.stringify({ original: current.original, improved: current.report.improved_prompt }),
    });
    $("out-original").textContent = out.original;
    $("out-improved").textContent = out.improved;
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
      li.innerHTML = `<span class="pill"></span><span class="hist-text"></span><button class="del" title="Delete">✕</button>`;
      li.querySelector(".pill").textContent = s.overall_score;
      li.querySelector(".hist-text").textContent = s.original_prompt;
      li.addEventListener("click", () => {
        $("prompt").value = s.original_prompt;
        renderReport(s.original_prompt, s.report);
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

loadHistory();
