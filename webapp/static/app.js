"use strict";

const $ = (id) => document.getElementById(id);

const fields = {
  authors: $("f-authors"),
  short_credential: $("f-credential"),
  qualifications: $("f-qualifications"),
  title: $("f-title"),
  publication: $("f-publication"),
  pub_date: $("f-pub-date"),
  access_date: $("f-access-date"),
  url: $("f-url"),
};

let currentQuote = "";
let lastPlain = "";
let lastHtml = "";

// --- gather the editable fields into the API shape ---
function collectFields() {
  return {
    url: fields.url.value.trim(),
    quote: currentQuote,
    authors: fields.authors.value.split("\n").map((s) => s.trim()).filter(Boolean),
    short_credential: fields.short_credential.value.trim() || null,
    qualifications: fields.qualifications.value.trim() || null,
    title: fields.title.value.trim() || null,
    publication: fields.publication.value.trim() || null,
    pub_date: fields.pub_date.value || null,
    access_date: fields.access_date.value || null,
    page_number: null,
  };
}

// --- live preview (debounced) ---
let formatTimer = null;
function scheduleFormat() {
  clearTimeout(formatTimer);
  formatTimer = setTimeout(refreshPreview, 350);
}

async function refreshPreview() {
  try {
    const r = await fetch("/api/format", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectFields()),
    });
    const data = await r.json();
    lastPlain = data.plain;
    lastHtml = data.html;
    $("preview").innerHTML = data.html;
  } catch (e) {
    $("preview").textContent = "Could not render preview.";
  }
}

// --- warnings ---
function showWarnings(list) {
  const box = $("warnings");
  if (!list || list.length === 0) { box.hidden = true; box.innerHTML = ""; return; }
  box.hidden = false;
  box.innerHTML =
    "<strong>Check before you use this:</strong><ul>" +
    list.map((w) => `<li>${escapeHtml(w)}</li>`).join("") +
    "</ul>";
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// --- populate fields from a scrape response ---
function fillFields(f) {
  fields.authors.value = (f.authors || []).join("\n");
  fields.short_credential.value = f.short_credential || "";
  fields.qualifications.value = f.qualifications || "";
  fields.title.value = f.title || "";
  fields.publication.value = f.publication || "";
  fields.pub_date.value = f.pub_date || "";
  fields.access_date.value = f.access_date || "";
  fields.url.value = f.url || "";
}

// --- credential drafting (best-effort; falls back to manual) ---
function setCredStatus(text, isError) {
  const cs = $("cred-status");
  cs.className = "status cred-status" + (isError ? " error" : "");
  cs.textContent = text;
}

async function draftCredentials(f) {
  setCredStatus("Drafting author credentials via web search… this can take up to a minute.");
  try {
    const r = await fetch("/api/credentials", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ authors: f.authors || [], publication: f.publication, url: f.url }),
    });
    if (r.status === 429) {
      setCredStatus("Credential drafting is rate-limited right now — enter credentials manually.", true);
      return;
    }
    if (!r.ok) { // 503 (no key) etc. -> leave manual
      setCredStatus("Credential drafting unavailable — enter credentials manually.", true);
      return;
    }
    const data = await r.json();
    let filled = false;
    if (data.short_credential && !fields.short_credential.value) {
      fields.short_credential.value = data.short_credential; filled = true;
    }
    if (data.qualifications && !fields.qualifications.value) {
      fields.qualifications.value = data.qualifications; filled = true;
    }
    if (filled) {
      setCredStatus("Draft filled in — verify it against the source before using.");
      appendWarning("Credentials were AI-drafted — verify them against the source.");
      refreshPreview();
    } else {
      setCredStatus("Couldn't verify this author's credentials — enter them manually.", true);
    }
  } catch (e) {
    setCredStatus("Credential drafting failed — enter credentials manually.", true);
  }
}

function appendWarning(text) {
  const box = $("warnings");
  box.hidden = false;
  if (!box.querySelector("ul")) box.innerHTML = "<strong>Check before you use this:</strong><ul></ul>";
  const li = document.createElement("li");
  li.textContent = text;
  box.querySelector("ul").appendChild(li);
}

// --- submit: scrape ---
$("scrape-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = $("in-url").value.trim();
  currentQuote = $("in-quote").value;
  const status = $("intake-status");
  const btn = $("build-btn");
  status.className = "status";
  status.textContent = "Fetching and reading the article…";
  btn.disabled = true;
  try {
    const r = await fetch("/api/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, quote: currentQuote }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      status.className = "status error";
      status.textContent = err.error || "Could not read that page.";
      return;
    }
    const data = await r.json();
    fillFields(data.fields);
    showWarnings(data.warnings);
    $("workspace").hidden = false;
    status.textContent = "";
    await refreshPreview();
    draftCredentials(data.fields);
  } catch (e) {
    status.className = "status error";
    status.textContent = "Network error — try again.";
  } finally {
    btn.disabled = false;
  }
});

// re-render preview whenever a field changes
Object.values(fields).forEach((el) => el.addEventListener("input", scheduleFormat));

// --- copy buttons ---
$("copy-html").addEventListener("click", async () => {
  try {
    await navigator.clipboard.write([
      new ClipboardItem({
        "text/html": new Blob([lastHtml], { type: "text/html" }),
        "text/plain": new Blob([lastPlain], { type: "text/plain" }),
      }),
    ]);
    flashCopy("Copied — paste into Google Docs.");
  } catch (e) {
    await navigator.clipboard.writeText(lastPlain);
    flashCopy("Copied as plain text.");
  }
});

$("copy-plain").addEventListener("click", async () => {
  await navigator.clipboard.writeText(lastPlain);
  flashCopy("Copied plain text.");
});

function flashCopy(msg) {
  const s = $("copy-status");
  s.textContent = msg;
  setTimeout(() => (s.textContent = ""), 2500);
}
