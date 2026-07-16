"use strict";

const state = { report: null, history: [], filtered: [] };
const $ = (selector) => document.querySelector(selector);

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");

function formatDate(value, withTime = false) {
  if (!value) return "No disponible";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ca-ES", {
    timeZone: "Europe/Paris", day: "2-digit", month: "2-digit", year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {})
  }).format(date);
}

function formatNumber(value) {
  if (value === null || value === undefined) return "No especificat";
  return new Intl.NumberFormat("ca-ES", { maximumFractionDigits: 2 }).format(value);
}

function statusMeta(status) {
  return {
    success: ["status-success", "✓", "Dades actualitzades"],
    partial: ["status-partial", "!", "Dades parcials"],
    error: ["status-error", "×", "Error de verificació"]
  }[status] || ["status-loading", "◌", "Estat desconegut"];
}

function documentStatus(status) {
  return {
    nou: ["status-new", "Nou"],
    actualitzat: ["status-updated", "Actualitzat"],
    "sense canvis": ["status-unchanged", "Sense canvis"],
    error: ["status-error", "Error"]
  }[status] || ["status-unchanged", status];
}

function renderHeader(report, attempt) {
  const effectiveStatus = attempt?.status || report.status;
  const [className, icon, label] = statusMeta(effectiveStatus);
  $("#global-status").className = `status-pill ${className}`;
  $("#global-status").innerHTML = `<span aria-hidden="true">${icon}</span> ${label}`;
  $("#updated-at").textContent = formatDate(attempt?.attempted_at || report.generated_at, true);
  const runUrl = attempt?.actions_run_url || report.actions_run_url;
  if (runUrl) {
    $("#run-link").href = runUrl;
    $("#run-link").classList.remove("is-hidden");
  }
  const age = Date.now() - new Date(report.generated_at).getTime();
  $("#stale-warning").classList.toggle("is-hidden", age <= 26 * 60 * 60 * 1000);
}

function renderPriority(report) {
  const card = $("#priority-alert");
  const count = report.summary.interesting_count;
  card.className = `priority-card ${report.status === "error" ? "priority-error" : count ? "priority-positive" : "priority-negative"}`;
  card.querySelector(".priority-icon").textContent = report.status === "error" ? "×" : count ? "✓" : "–";
  $("#priority-title").textContent = count
    ? `${count} ${count === 1 ? "oferta prioritària detectada" : "ofertes prioritàries detectades"}`
    : "Cap oferta GE o CLA detectada";
  $("#priority-copy").textContent = count
    ? "Les ofertes destacades apareixen en primer lloc i també es poden filtrar a la taula."
    : "No s’ha trobat cap coincidència exacta en la darrera verificació.";
  const counts = report.summary.interesting_by_specialty || {};
  $("#priority-counts").innerHTML = ["GE", "CLA"]
    .map(code => `<span class="specialty-chip">${code} · ${counts[code] || 0}</span>`).join("");
}

function renderMetrics(report) {
  const summary = report.summary;
  const documents = summary.documents;
  const cards = [
    ["Ofertes detectades", summary.offers_count, "Cada fila publicada compta com una oferta"],
    ["Volum de places", formatNumber(summary.vacancies_total), "Suma de les quotitats disponibles"],
    ["Territoris actius", `${summary.active_regions} / ${report.regions.length}`, "Amb almenys una oferta publicada"],
    ["Documents amb canvis", documents.new + documents.updated + (documents.removed || 0), `${documents.new} nous · ${documents.updated} actualitzats · ${documents.removed || 0} retirats`]
  ];
  $("#metrics").innerHTML = cards.map(([label, value, note]) =>
    `<article class="metric-card"><p>${escapeHtml(label)}</p><strong>${escapeHtml(value)}</strong><small>${escapeHtml(note)}</small></article>`
  ).join("");
  $("#top-specialties").innerHTML = `<strong>Especialitats més representades:</strong> ${
    summary.top_specialties.length
      ? summary.top_specialties.map(item => `<span class="specialty-chip">${escapeHtml(item.code)} · ${item.count}</span>`).join("")
      : "<span>No hi ha dades disponibles</span>"
  }`;
}

function renderRegions(report) {
  $("#regions").innerHTML = report.regions.map(region => {
    const specialties = Object.entries(region.specialties || {});
    const sources = region.documents.map(document => {
      const [className, label] = documentStatus(document.status);
      return `<li><a href="${escapeHtml(document.url)}" target="_blank" rel="noopener">${escapeHtml(document.title || "Document oficial")} <span aria-hidden="true">↗</span></a><span class="document-status ${className}">${label}</span></li>`;
    }).join("");
    const warnings = region.warnings.map(warning => `<li><strong>Avís:</strong> ${escapeHtml(warning)}</li>`).join("");
    return `<article class="region-card">
      <div class="region-head"><div><h3>${escapeHtml(region.name)}</h3>
      <p class="region-statline"><strong>${region.offers_count}</strong> ofertes · <strong>${escapeHtml(formatNumber(region.vacancies_total))}</strong> places</p></div>
      <span class="specialty-chip">${region.interesting_count} GE/CLA</span></div>
      <p><strong>Especialitats principals:</strong> ${region.top_specialties.length ? region.top_specialties.map(item => `${escapeHtml(item.code)} (${item.count})`).join(", ") : "cap"}</p>
      <div class="distribution">${specialties.map(([code, count]) => `<span>${escapeHtml(code)} · ${count}</span>`).join("")}</div>
      ${warnings ? `<ul class="warning-list">${warnings}</ul>` : ""}
      <details><summary>Fonts i documents analitzats</summary>
        <p><a href="${escapeHtml(region.page_url)}" target="_blank" rel="noopener">Pàgina oficial del territori <span aria-hidden="true">↗</span></a></p>
        <ul class="source-list">${sources || "<li>No hi ha cap document disponible.</li>"}</ul>
      </details>
    </article>`;
  }).join("");
}

function populateFilters(report) {
  const regions = [...new Set(report.offers.map(offer => offer.region))].sort((a, b) => a.localeCompare(b, "ca"));
  const specialties = [...new Set(report.offers.map(offer => offer.specialty))].sort((a, b) => a.localeCompare(b, "ca"));
  $("#region-filter").insertAdjacentHTML("beforeend", regions.map(value => `<option>${escapeHtml(value)}</option>`).join(""));
  $("#specialty-filter").insertAdjacentHTML("beforeend", specialties.map(value => `<option>${escapeHtml(value)}</option>`).join(""));
}

function renderOffers() {
  const query = $("#search").value.trim().toLocaleLowerCase("ca");
  const region = $("#region-filter").value;
  const specialty = $("#specialty-filter").value;
  const targetOnly = $("#target-only").checked;
  const sortBy = $("#sort-filter").value;
  const targets = new Set(state.report.targets);
  state.filtered = state.report.offers.filter(offer => {
    const haystack = [offer.region, offer.specialty, offer.identifier, offer.institution, offer.municipality, offer.detail].join(" ").toLocaleLowerCase("ca");
    return (!query || haystack.includes(query))
      && (!region || offer.region === region)
      && (!specialty || offer.specialty === specialty)
      && (!targetOnly || targets.has(offer.specialty.replaceAll(" ", "").toUpperCase()));
  }).sort((a, b) => String(a[sortBy] || "zzzz").localeCompare(String(b[sortBy] || "zzzz"), "ca"));

  $("#offers-body").innerHTML = state.filtered.map(offer => {
    const [className, statusLabel] = documentStatus(offer.document_status);
    return `<tr>
      <td data-label="Territori">${escapeHtml(offer.region)}</td>
      <td data-label="Especialitat"><span class="specialty-chip">${escapeHtml(offer.specialty)}</span></td>
      <td data-label="Identificador">${escapeHtml(offer.identifier || "No disponible")}</td>
      <td data-label="Centre">${escapeHtml(offer.institution || "No especificat")}</td>
      <td data-label="Municipi">${escapeHtml(offer.municipality || "No especificat")}</td>
      <td data-label="Places">${escapeHtml(formatNumber(offer.vacancies))}</td>
      <td data-label="Data límit">${escapeHtml(offer.deadline || "No especificada")}</td>
      <td data-label="Document"><a class="pdf-link" href="${escapeHtml(offer.document_url)}" target="_blank" rel="noopener">Obre el PDF <span aria-hidden="true">↗</span></a><br><span class="document-status ${className}">${statusLabel}</span></td>
    </tr>`;
  }).join("");
  $("#result-count").textContent = `${state.filtered.length} ${state.filtered.length === 1 ? "oferta visible" : "ofertes visibles"}`;
  $("#empty-results").classList.toggle("is-hidden", state.filtered.length > 0);
}

function renderHistory(entries) {
  if (!entries.length) {
    $("#history").innerHTML = `<div class="empty-state"><span aria-hidden="true">◷</span><h3>Encara no hi ha prou historial</h3><p>Les comparacions apareixeran després de les properes verificacions.</p></div>`;
    return;
  }
  $("#history").innerHTML = entries.map(entry => {
    const [className, icon, label] = statusMeta(entry.status);
    return `<article class="history-row">
      <p class="history-date"><strong>${formatDate(entry.generated_at)}</strong><span class="status-pill ${className}"><span aria-hidden="true">${icon}</span>${label}</span></p>
      <p><strong>${entry.offers_count}</strong> ofertes · <strong>${escapeHtml(formatNumber(entry.vacancies_total))}</strong> places</p>
      <p><strong>${entry.interesting_count}</strong><br><span class="history-change">GE / CLA</span></p>
      <p><strong>+${entry.changes.added}</strong><br><span class="history-change">afegides</span></p>
      <p><strong>−${entry.changes.removed}</strong><br><span class="history-change">retirades</span></p>
    </article>`;
  }).join("");
}

function showLoadError(error) {
  $("#global-status").className = "status-pill status-error";
  $("#global-status").innerHTML = '<span aria-hidden="true">×</span> No s’han pogut carregar les dades';
  const card = $("#priority-alert");
  card.className = "priority-card priority-error";
  card.querySelector(".priority-icon").textContent = "×";
  $("#priority-title").textContent = "No s’ha pogut obrir el darrer informe";
  $("#priority-copy").textContent = "Torneu-ho a provar més tard o consulteu l’execució de GitHub Actions.";
  console.error(error);
}

async function start() {
  try {
    const [reportResponse, statusResponse, historyResponse] = await Promise.all([
      fetch("data/latest.json", { cache: "no-store" }),
      fetch("data/status.json", { cache: "no-store" }),
      fetch("data/history/index.json", { cache: "no-store" })
    ]);
    if (!reportResponse.ok) throw new Error("No hi ha cap informe publicat.");
    state.report = await reportResponse.json();
    const attempt = statusResponse.ok ? await statusResponse.json() : null;
    const history = historyResponse.ok ? await historyResponse.json() : { entries: [] };
    state.history = history.entries || [];
    renderHeader(state.report, attempt);
    renderPriority(state.report);
    renderMetrics(state.report);
    renderRegions(state.report);
    populateFilters(state.report);
    renderOffers();
    renderHistory(state.history);
  } catch (error) {
    showLoadError(error);
  }
}

$("#filters").addEventListener("input", renderOffers);
$("#filters").addEventListener("change", renderOffers);
$("#filters").addEventListener("reset", () => window.setTimeout(renderOffers));
start();
