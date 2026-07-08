"use strict";

const $ = (sel) => document.querySelector(sel);
let LANGS = [];
let MODELS = [];
let modelsTimer = null;

/* ---------- onglets ---------- */
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("#tab-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "models") refreshModels();
  });
});

/* ---------- helpers ---------- */
async function api(path, opts) {
  const resp = await fetch(path, opts);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || resp.statusText);
  return data;
}

function fillLangSelect(select, withAuto) {
  select.innerHTML = withAuto ? '<option value="auto">Détection automatique</option>' : "";
  for (const l of LANGS) {
    const opt = document.createElement("option");
    opt.value = l.code;
    opt.textContent = `${l.name} (${l.code})`;
    select.appendChild(opt);
  }
}

/* ---------- initialisation ---------- */
async function init() {
  const data = await api("/api/languages");
  LANGS = data.languages;
  fillLangSelect($("#source"), true);
  fillLangSelect($("#target"), false);
  $("#target").value = "fr";
  for (const f of data.output_formats) {
    const opt = document.createElement("option");
    opt.value = f;
    opt.textContent = f;
    $("#out-format").appendChild(opt);
  }
  await refreshModelSelect();
}

async function refreshModelSelect() {
  const data = await api("/api/models");
  MODELS = data.models;
  const select = $("#model");
  select.innerHTML = "";
  let firstUsable = null;
  for (const m of MODELS) {
    const opt = document.createElement("option");
    opt.value = m.id;
    const offline = m.offline ? "" : " — EN LIGNE";
    opt.textContent = m.label + (m.installed ? "" : " (non installé)") + offline;
    opt.disabled = !m.installed;
    if (m.installed && m.offline && firstUsable === null) firstUsable = m.id;
    select.appendChild(opt);
  }
  if (firstUsable) select.value = firstUsable;
  const anyOffline = MODELS.some((m) => m.installed && m.offline);
  $("#model-hint").textContent = anyOffline
    ? ""
    : "Aucun modèle hors ligne installé : voir l'onglet « Modèles ».";
}

/* ---------- fichier ---------- */
const dropzone = $("#dropzone");
const fileInput = $("#file");
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    showFile();
  }
});
fileInput.addEventListener("change", showFile);
function showFile() {
  const f = fileInput.files[0];
  if (f) {
    dropzone.classList.add("hasfile");
    $("#dropzone-label").innerHTML = `📄 ${f.name} <small>(cliquer pour changer)</small>`;
  }
}

/* ---------- job ---------- */
$("#job-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = fileInput.files[0];
  if (!f) { alert("Choisir un fichier de sous-titres."); return; }
  const form = new FormData();
  form.append("file", f);
  form.append("source", $("#source").value);
  form.append("target", $("#target").value);
  form.append("model", $("#model").value);
  form.append("out_format", $("#out-format").value);

  $("#submit-btn").disabled = true;
  $("#job-status").hidden = false;
  $("#job-download").hidden = true;
  setJobUI(0, "Envoi du fichier…", "");
  try {
    const job = await api("/api/jobs", { method: "POST", body: form });
    pollJob(job.id);
  } catch (err) {
    setJobUI(1, "Erreur : " + err.message, "error");
    $("#submit-btn").disabled = false;
  }
});

function setJobUI(progress, message, state) {
  const bar = $("#job-bar");
  bar.style.width = Math.round(progress * 100) + "%";
  bar.className = "bar" + (state ? " " + state : "");
  const msg = $("#job-message");
  msg.textContent = message;
  msg.className = state === "error" ? "error" : "";
}

async function pollJob(id) {
  try {
    const job = await api("/api/jobs/" + id);
    if (job.status === "done") {
      const detected = job.detected ? ` (langue détectée : ${job.detected})` : "";
      setJobUI(1, "Terminé" + detected + " — " + job.output_name, "done");
      const link = $("#job-download");
      link.href = `/api/jobs/${id}/download`;
      link.hidden = false;
      $("#submit-btn").disabled = false;
    } else if (job.status === "error") {
      setJobUI(1, "Erreur : " + job.error, "error");
      $("#submit-btn").disabled = false;
    } else {
      const detected = job.detected ? ` — langue détectée : ${job.detected}` : "";
      setJobUI(job.progress, `Traduction en cours… ${Math.round(job.progress * 100)} %${detected}`, "");
      setTimeout(() => pollJob(id), 800);
    }
  } catch (err) {
    setJobUI(1, "Erreur : " + err.message, "error");
    $("#submit-btn").disabled = false;
  }
}

/* ---------- onglet modèles ---------- */
async function refreshModels() {
  const data = await api("/api/models");
  MODELS = data.models;
  renderModels();
  const installing = MODELS.some((m) => Object.values(m.tasks).some((t) => t.status === "installing"));
  clearTimeout(modelsTimer);
  if (installing && $("#tab-models").classList.contains("active")) {
    modelsTimer = setTimeout(refreshModels, 1500);
  }
  refreshModelSelect();
}

function langOptions() {
  return LANGS.map((l) => `<option value="${l.code}">${l.name} (${l.code})</option>`).join("");
}

function renderModels() {
  const root = $("#models-list");
  root.innerHTML = "";
  for (const m of MODELS) {
    const card = document.createElement("div");
    card.className = "model-card";
    const offlineBadge = m.offline
      ? '<span class="badge ok">hors ligne</span>'
      : '<span class="badge warn">en ligne</span>';
    let body = `
      <div class="badges">${offlineBadge}<span class="badge">${m.size}</span></div>
      <h3>${m.label}</h3>
      <p class="desc">${m.description}</p>`;

    if (m.kind === "single") {
      body += m.installed
        ? `<button class="small danger" data-action="uninstall" data-model="${m.id}">Désinstaller</button>`
        : `<button class="small" data-action="install" data-model="${m.id}">Installer</button>`;
    } else if (m.kind === "pairs") {
      const chips = (m.pairs || []).map((p) =>
        `<span class="pair-chip">${p.from} → ${p.to}
          <button title="Désinstaller" data-action="uninstall" data-model="${m.id}" data-pair="${p.from}:${p.to}">✕</button>
        </span>`).join("");
      body += `<div class="pairs">${chips || '<small class="desc">Aucune paire installée.</small>'}</div>
        <div class="pair-form">
          <select id="argos-from">${langOptions()}</select>
          <span>→</span>
          <select id="argos-to">${langOptions()}</select>
          <button class="small" data-action="install" data-model="${m.id}" data-pairform="1">Installer la paire</button>
        </div>
        <small class="desc">Si la paire directe n'existe pas, installer <em>source → en</em> puis <em>en → cible</em> (pivot).</small>`;
    } else if (m.kind === "api") {
      body += `
        <div class="pair-form">
          <input type="text" id="lt-url" placeholder="URL de l'instance (ex. http://192.168.1.10:5000)">
          <input type="text" id="lt-key" placeholder="Clé API (optionnelle)">
          <button class="small" data-action="save-config">Enregistrer</button>
        </div>`;
    }

    for (const [key, task] of Object.entries(m.tasks || {})) {
      const label = key.includes(":") ? key.split(":").slice(1).join(" → ") : m.label;
      if (task.status === "installing") {
        body += `<div class="task-line">Installation de ${label}… ${Math.round(task.progress * 100)} %</div>
          <div class="progress mini-progress"><div class="bar" style="width:${Math.round(task.progress * 100)}%"></div></div>`;
      } else if (task.status === "error") {
        body += `<div class="task-line error">Échec de l'installation (${label}) : ${task.error}</div>`;
      }
    }

    card.innerHTML = body;
    root.appendChild(card);
  }

  if ($("#lt-url")) {
    api("/api/config").then((cfg) => {
      $("#lt-url").value = cfg.libretranslate_url || "";
      $("#lt-key").value = cfg.libretranslate_api_key || "";
    });
  }

  root.querySelectorAll("button[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => handleModelAction(btn));
  });
}

async function handleModelAction(btn) {
  const action = btn.dataset.action;
  try {
    if (action === "save-config") {
      await api("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          libretranslate_url: $("#lt-url").value.trim(),
          libretranslate_api_key: $("#lt-key").value.trim(),
        }),
      });
      btn.textContent = "Enregistré ✓";
      setTimeout(() => (btn.textContent = "Enregistrer"), 1500);
      return;
    }
    const body = { model_id: btn.dataset.model };
    if (btn.dataset.pairform) {
      const from = $("#argos-from").value, to = $("#argos-to").value;
      if (from === to) { alert("Choisir deux langues différentes."); return; }
      body.pair = `${from}:${to}`;
    } else if (btn.dataset.pair) {
      body.pair = btn.dataset.pair;
    }
    if (action === "uninstall" && !confirm("Désinstaller ce modèle ?")) return;
    await api(`/api/models/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    refreshModels();
  } catch (err) {
    alert("Erreur : " + err.message);
  }
}

init().catch((err) => alert("Erreur d'initialisation : " + err.message));
