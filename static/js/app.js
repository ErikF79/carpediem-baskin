const API = window.CarpeDiemAPI || "";
const state = {
  config: null,
  matches: [],
  players: [],
  view: "calendar",
  federation: "",
  cursor: new Date(),
  isStaff: false,
};

const MESI = [
  "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
  "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
];
const MESI_BREVE = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
const GIORNI = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"];

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html !== undefined) n.innerHTML = html;
  return n;
};

function pad(n) { return String(n).padStart(2, "0"); }
function toKey(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function parseDate(s) { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); }
function fmtTime(t) { return t ? t.slice(0, 5) : ""; }
function initials(name) {
  return name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.status === 204 ? null : res.json();
}

function opponentOf(m) {
  const home = m.home_team.is_ours;
  return { opponent: home ? m.away_team : m.home_team, home };
}

function teamLogoImg(team, cls) {
  if (!team || !team.logo_url) return null;
  const img = el("img", cls || "team-logo");
  img.src = team.logo_url;
  img.alt = team.name;
  img.loading = "lazy";
  img.referrerPolicy = "no-referrer";
  img.onerror = () => img.remove();
  return img;
}

/* ------------------------------- Theme -------------------------------- */
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  $("#themeToggle").textContent = theme === "dark" ? "☀️" : "🌙";
  localStorage.setItem("cd_theme", theme);
}

/* ------------------------------- Toast -------------------------------- */
let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("is-show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("is-show"), 2600);
}

/* ------------------------------ Loaders ------------------------------- */
async function loadConfig() {
  state.config = await api("/api/config");
  $("#appName").textContent = state.config.app_name;
  document.title = state.config.app_name;
  renderFooterFeds();
}
function renderFooterFeds() {
  const box = $("#footerFeds");
  box.innerHTML = "";
  (state.config?.federations || []).forEach((f) => {
    if (!f.logo_url) return;
    const img = el("img");
    img.src = f.logo_url;
    img.alt = f.name;
    img.title = f.name;
    box.appendChild(img);
  });
}

async function loadMatches() {
  const q = state.federation ? `?federation=${state.federation}` : "";
  state.matches = await api("/api/matches" + q);
  render();
}

window.refreshPublic = async function () {
  try {
    await Promise.all([loadMatches(), loadPlayers()]);
  } catch {
    /* ignore */
  }
};

/* ------------------------------ Render -------------------------------- */
function render() {
  if (state.view === "calendar") renderCalendar();
  else if (state.view === "agenda") renderAgenda();
  else if (state.view === "roster") renderRoster();
}

async function loadPlayers() {
  state.players = await api("/api/players");
}

const ROLE_NAMES = {
  1: "Ruolo 1 — regista",
  2: "Ruolo 2",
  3: "Ruolo 3",
  4: "Ruolo 4",
  5: "Ruolo 5",
  6: "Ruolo 6",
};

function renderRoster() {
  const box = $("#rosterView");
  box.innerHTML = "";
  if (!state.players.length) {
    box.appendChild(el("p", "match-card__meta", "Nessun giocatore caricato."));
    return;
  }
  const byRole = {};
  state.players.forEach((p) => { (byRole[p.role] = byRole[p.role] || []).push(p); });

  const head = el("div", "cal-head");
  head.appendChild(el("h2", null, "La nostra squadra"));
  head.appendChild(el("span", "match-card__meta", `${state.players.length} giocatori`));
  box.appendChild(head);

  Object.keys(byRole).sort().forEach((role) => {
    const grp = el("div", "roster-group");
    grp.appendChild(el("h3", null, ROLE_NAMES[role] || `Ruolo ${role}`));
    const grid = el("div", "roster-grid");
    byRole[role].forEach((p) => grid.appendChild(playerCard(p)));
    grp.appendChild(grid);
    box.appendChild(grp);
  });
}

function playerCard(p) {
  const card = el("div", "player-card");
  const media = el("div", "player-card__media");
  if (p.photo_url) {
    const img = el("img");
    img.src = p.photo_url;
    img.alt = `${p.first_name} ${p.last_name}`;
    img.loading = "lazy";
    img.referrerPolicy = "no-referrer";
    img.onerror = () => { img.replaceWith(avaNode(p, true)); };
    media.appendChild(img);
  } else {
    media.appendChild(avaNode(p, true));
  }
  card.appendChild(media);
  const info = el("div", "player-card__info");
  info.appendChild(el("div", "player-card__name", `${p.first_name} ${p.last_name}`));
  const tags = el("div", "player-card__tags");
  tags.appendChild(el("span", "role", p.role2_type || `R${p.role}`));
  (p.federations || []).forEach((f) => tags.appendChild(el("span", `pill ${f.code}`, f.code)));
  if (p.code_eisi) info.appendChild(el("div", "player-card__code", `EISI ${p.code_eisi}`));
  if (p.code_csain) info.appendChild(el("div", "player-card__code", `CSAIN ${p.code_csain}`));
  info.appendChild(tags);
  card.appendChild(info);
  return card;
}

function renderCalendar() {
  const box = $("#calendarView");
  box.innerHTML = "";
  const y = state.cursor.getFullYear();
  const mo = state.cursor.getMonth();

  const head = el("div", "cal-head");
  head.appendChild(el("h2", null, `${MESI[mo]} ${y}`));
  const nav = el("div", "cal-nav");
  const prev = el("button", "btn", "‹");
  const next = el("button", "btn", "›");
  prev.onclick = () => { state.cursor = new Date(y, mo - 1, 1); render(); };
  next.onclick = () => { state.cursor = new Date(y, mo + 1, 1); render(); };
  nav.append(prev, next);
  head.appendChild(nav);
  box.appendChild(head);

  const byDay = {};
  state.matches.forEach((m) => {
    const k = m.match_date;
    (byDay[k] = byDay[k] || []).push(m);
  });

  const grid = el("div", "cal-grid");
  GIORNI.forEach((g) => grid.appendChild(el("div", "cal-dow", g)));

  const first = new Date(y, mo, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const gridStart = new Date(y, mo, 1 - startOffset);
  const todayKey = toKey(new Date());

  for (let i = 0; i < 42; i++) {
    const d = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i);
    const key = toKey(d);
    const cell = el("div", "cal-cell");
    if (d.getMonth() !== mo) cell.classList.add("is-out");
    if (key === todayKey) cell.classList.add("is-today");
    cell.appendChild(el("div", "cal-day", String(d.getDate())));
    (byDay[key] || []).forEach((m) => cell.appendChild(eventEl(m)));
    grid.appendChild(cell);
  }
  box.appendChild(grid);
}

function eventEl(m) {
  const { opponent, home } = opponentOf(m);
  const ev = el("div", `ev fed-${m.federation.code}`);
  ev.appendChild(el("span", `ev__badge badge-${m.federation.code}`, m.federation.code));
  const line = el("span", "ev__line");
  const lg = teamLogoImg(opponent, "ev__logo");
  if (lg) line.appendChild(lg);
  else line.appendChild(el("span", "ev__logo ev__logo--fallback", initials(opponent.name)));
  line.appendChild(el("span", "ev__time", fmtTime(m.match_time)));
  line.appendChild(el("span", "ev__dir", home ? "vs" : "@"));
  ev.appendChild(line);
  ev.appendChild(el("span", "ev__vs", opponent.name));
  ev.onclick = () => openMatch(m.id);
  return ev;
}

function renderAgenda() {
  const box = $("#agendaView");
  box.innerHTML = "";
  if (!state.matches.length) {
    box.appendChild(el("p", "match-card__meta", "Nessuna gara in programma."));
    return;
  }
  const groups = {};
  state.matches.forEach((m) => {
    const d = parseDate(m.match_date);
    const k = `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
    (groups[k] = groups[k] || []).push(m);
  });
  Object.keys(groups).sort().forEach((k) => {
    const [gy, gm] = k.split("-").map(Number);
    const g = el("div", "agenda-group");
    g.appendChild(el("h3", null, `${MESI[gm - 1]} ${gy}`));
    groups[k].forEach((m) => g.appendChild(matchCard(m)));
    box.appendChild(g);
  });
}

function matchCard(m) {
  const { opponent, home } = opponentOf(m);
  const d = parseDate(m.match_date);
  const card = el("div", `match-card fed-${m.federation.code}`);
  card.onclick = () => openMatch(m.id);

  const dt = el("div", "match-card__date");
  dt.appendChild(el("div", "match-card__day", String(d.getDate())));
  dt.appendChild(el("div", "match-card__mon", MESI_BREVE[d.getMonth()]));
  card.appendChild(dt);

  const main = el("div", "match-card__main");
  const titleRow = el("div", "match-card__titleRow");
  const lg = teamLogoImg(opponent, "match-card__logo");
  if (lg) titleRow.appendChild(lg);
  titleRow.appendChild(el("div", "match-card__vs", `${home ? "vs" : "@"} ${opponent.name}`));
  main.appendChild(titleRow);
  const meta = el("div", "match-card__meta");
  meta.appendChild(el("span", null, `🕒 ${fmtTime(m.match_time) || "da definire"}`));
  if (m.venue) meta.appendChild(el("span", null, `📍 ${m.venue.name}`));
  if (m.matchday) meta.appendChild(el("span", null, `Giornata ${m.matchday}`));
  main.appendChild(meta);
  card.appendChild(main);

  const right = el("div", "match-card__right");
  const pill = el("span", `pill ${m.federation.code}`, m.federation.code);
  right.appendChild(pill);
  if (m.home_score !== null && m.away_score !== null) {
    const our = m.home_team.is_ours ? m.home_score : m.away_score;
    const opp = m.home_team.is_ours ? m.away_score : m.home_score;
    right.appendChild(el("span", "match-card__score", `${our}-${opp}`));
    right.appendChild(el("span", "pill result", "Risultato"));
  }
  card.appendChild(right);

  // Icone di stato (attive se presenti dati, altrimenti inattive)
  const icons = el("div", "card-icons", "");
  const bConv = el("span", "icon-badge", "📋");
  bConv.title = "Convocazioni"; bConv.dataset.type = "convocazioni";
  bConv.onclick = (e) => { e.stopPropagation(); openIconPopup(m.id, "convocazioni"); };
  icons.appendChild(bConv);

  const bUnav = el("span", "icon-badge", "🚫");
  bUnav.title = "Indisponibili"; bUnav.dataset.type = "indisponibili";
  bUnav.onclick = (e) => { e.stopPropagation(); openIconPopup(m.id, "indisponibili"); };
  icons.appendChild(bUnav);

  const bPass = el("span", "icon-badge", "🚌");
  bPass.title = "Passaggi"; bPass.dataset.type = "passaggi";
  bPass.onclick = (e) => { e.stopPropagation(); openIconPopup(m.id, "passaggi"); };
  icons.appendChild(bPass);
  card.appendChild(icons);

  // Attiva le icone solo se esistono dati reali per questa gara
  (async () => {
    try {
      const detail = await api(`/api/matches/${m.id}`);
      if ((detail.convocations || []).length) card.querySelector('.icon-badge[data-type="convocazioni"]').classList.add('active');
      if ((detail.unavailabilities || []).length) card.querySelector('.icon-badge[data-type="indisponibili"]').classList.add('active');
      if ((detail.transport || []).length || (detail.notes && detail.notes.trim())) card.querySelector('.icon-badge[data-type="passaggi"]').classList.add('active');
    } catch { /* lascia inattive */ }
  })();

  return card;
}

/* --------------------------- Match detail ----------------------------- */
async function openMatch(id) {
  const body = $("#modalBody");
  body.innerHTML = "<p>Caricamento…</p>";
  openModal();
  try {
    const m = await api(`/api/matches/${id}`);
    body.innerHTML = "";
    body.appendChild(detailNode(m));
  } catch {
    body.innerHTML = "<p>Errore nel caricamento della gara.</p>";
  }
}

function detailNode(m) {
  const { opponent, home } = opponentOf(m);
  const d = parseDate(m.match_date);
  const wrap = el("div");

  const head = el("div", "detail-head");
  head.appendChild(el("span", `pill ${m.federation.code}`, m.federation.code));
  head.appendChild(el("span", null, m.competition || ""));
  wrap.appendChild(head);

  const logoRow = el("div", "detail-logos");
  logoRow.appendChild(detailTeam(m.home_team));
  logoRow.appendChild(el("span", "detail-vs", "VS"));
  logoRow.appendChild(detailTeam(m.away_team));
  wrap.appendChild(logoRow);

  wrap.appendChild(el("h2", "detail-title", `${home ? "vs" : "@"} ${opponent.name}`));
  if (m.home_score !== null && m.away_score !== null) {
    wrap.appendChild(el("p", null, `<strong>Risultato:</strong> ${m.home_score} - ${m.away_score}`));
  }

  const rows = el("div", "detail-rows");
  rows.appendChild(row("📅", `${GIORNI[(d.getDay() + 6) % 7]} ${d.getDate()} ${MESI[d.getMonth()]} ${d.getFullYear()}`));
  rows.appendChild(row("🕒", fmtTime(m.match_time) || "Orario da definire"));
  if (m.matchday) rows.appendChild(row("🔢", `Giornata ${m.matchday}`));
  if (m.venue) {
    const r = el("div", "detail-row");
    r.appendChild(el("span", "detail-row__icon", "📍"));
    const label = el("span", null, `${m.venue.name}${m.venue.address ? " — " + m.venue.address : ""} `);
    if (m.venue.maps_url) {
      const a = el("a", null, "Apri in Google Maps");
      a.href = m.venue.maps_url;
      a.target = "_blank";
      a.rel = "noopener";
      label.appendChild(a);
    }
    r.appendChild(label);
    rows.appendChild(r);
  }
  wrap.appendChild(rows);

  if (m.notes) wrap.appendChild(el("p", "match-card__meta", m.notes));

  const starters = (m.convocations || []).filter((c) => c.kind === "starter").sort((a, b) => (a.slot_order || 0) - (b.slot_order || 0));
  const reserves = (m.convocations || []).filter((c) => c.kind === "reserve").sort((a, b) => (a.slot_order || 0) - (b.slot_order || 0));

  if (starters.length || (m.convocations || []).length) {
    const sec = el("div", "detail-section");
    sec.appendChild(el("h4", null, `Convocati (${starters.length || m.convocations.length}/14)`));
    sec.appendChild(playerChips(starters.length ? starters : m.convocations, false));
    if (reserves.length) {
      sec.appendChild(el("h4", null, `Riserve (${reserves.length}/2)`));
      sec.appendChild(playerChips(reserves, true));
    }
    wrap.appendChild(sec);
  } else {
    wrap.appendChild(el("p", "match-card__meta", "Convocazioni non ancora pubblicate."));
  }

  const unav = (m.unavailabilities || []);
  if (unav.length) {
    const sec = el("div", "detail-section");
    sec.appendChild(el("h4", null, "Indisponibili"));
    sec.appendChild(playerChips(unav.map((u) => ({ player: u.player, kind: "unavailable" })), true));
    wrap.appendChild(sec);
  }

  const share = el("button", "btn", "💬 Condividi su WhatsApp");
  share.style.marginTop = "22px";
  share.onclick = () => shareWhatsApp(m, opponent, home, d, starters, reserves);
  wrap.appendChild(share);
  return wrap;
}

function detailTeam(team) {
  const col = el("div", "detail-team" + (team.is_ours ? " is-ours" : ""));
  const lg = teamLogoImg(team, "detail-logo");
  if (lg) col.appendChild(lg);
  col.appendChild(el("span", "detail-team__name", team.name));
  return col;
}

function row(icon, text) {
  const r = el("div", "detail-row");
  r.appendChild(el("span", "detail-row__icon", icon));
  r.appendChild(el("span", null, text));
  return r;
}

function playerChips(items, reserve) {
  const chips = el("div", "chips");
  items.forEach((c) => {
    const p = c.player;
    const chip = el("div", "player-chip" + (reserve ? " reserve" : ""));
    if (p.photo_url) {
      const img = el("img");
      img.src = p.photo_url;
      img.referrerPolicy = "no-referrer";
      img.onerror = () => { img.replaceWith(avaNode(p)); };
      chip.appendChild(img);
    } else {
      chip.appendChild(avaNode(p));
    }
    chip.appendChild(el("span", null, `${p.first_name} ${p.last_name}`));
    chip.appendChild(el("span", "role", p.role2_type || `R${p.role}`));
    chips.appendChild(chip);
  });
  return chips;
}

function avaNode(p, big) {
  const a = el("span", "ava ava-imgfallback" + (big ? " ava--big" : ""), initials(`${p.first_name} ${p.last_name}`));
  return a;
}

function shareWhatsApp(m, opponent, home, d, starters, reserves) {
  const lines = [];
  lines.push(`🏀 ${state.config.app_name} — ${m.federation.code}`);
  lines.push(`${home ? "vs" : "@"} ${opponent.name}`);
  lines.push(`📅 ${GIORNI[(d.getDay() + 6) % 7]} ${d.getDate()} ${MESI[d.getMonth()]} ${d.getFullYear()} — ore ${fmtTime(m.match_time) || "TBD"}`);
  if (m.venue) lines.push(`📍 ${m.venue.name}`);
  if (m.venue?.maps_url) lines.push(m.venue.maps_url);
  if (starters.length) lines.push("", "Convocati:", starters.map((c) => `• ${c.player.first_name} ${c.player.last_name}`).join("\n"));
  if (reserves.length) lines.push("", "Riserve:", reserves.map((c) => `• ${c.player.first_name} ${c.player.last_name}`).join("\n"));
  const url = "https://wa.me/?text=" + encodeURIComponent(lines.join("\n"));
  window.open(url, "_blank");
}

/* ------------------------------- Modal -------------------------------- */
function openModal() { $("#modal").classList.add("is-open"); $("#modal").setAttribute("aria-hidden", "false"); }
function closeModal() { $("#modal").classList.remove("is-open"); $("#modal").setAttribute("aria-hidden", "true"); }

/* ------------------------------- Staff -------------------------------- */
async function toggleStaff() {
  if (state.isStaff) {
    await api("/api/admin/logout", { method: "POST" }).catch(() => {});
    state.isStaff = false;
    $("#staffToggle").textContent = "🔒";
    $("#staffTab").hidden = true;
    if (state.view === "admin") switchView("calendar");
    toast("Uscita dall'area staff");
    return;
  }
  const pw = prompt("Inserisci la password dello staff:");
  if (!pw) return;
  try {
    await api("/api/admin/login", { method: "POST", body: JSON.stringify({ password: pw }) });
    state.isStaff = true;
    $("#staffToggle").textContent = "🔓";
    $("#staffTab").hidden = false;
    toast("Accesso staff effettuato");
    switchView("admin");
  } catch {
    toast("Password errata");
  }
}

/* ------------------------------ Events -------------------------------- */
function switchView(view) {
  state.view = view;
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("is-active", x.dataset.view === view));
  ["calendar", "agenda", "roster", "admin"].forEach((v) =>
    $("#" + v + "View").classList.toggle("is-hidden", v !== view)
  );
  $("#filters").style.display = view === "calendar" ? "" : "none";
  if (view === "admin") {
    if (window.renderAdmin) window.renderAdmin();
  } else {
    render();
  }
}

function bind() {
  document.querySelectorAll(".tab").forEach((t) => {
    t.onclick = () => switchView(t.dataset.view);
  });
  document.querySelectorAll("#fedFilter .seg").forEach((s) => {
    s.onclick = () => {
      state.federation = s.dataset.fed;
      document.querySelectorAll("#fedFilter .seg").forEach((x) => x.classList.toggle("is-active", x === s));
      loadMatches();
    };
  });
  $("#todayBtn").onclick = () => { state.cursor = new Date(); if (state.view !== "calendar") { state.view = "calendar"; } render(); };
  $("#themeToggle").onclick = () => applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
  $("#staffToggle").onclick = toggleStaff;
  document.querySelectorAll("[data-close]").forEach((x) => { x.onclick = closeModal; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
}

/* ------------------------------- Init --------------------------------- */
async function init() {
  applyTheme(localStorage.getItem("cd_theme") || "light");
  bind();
  registerServiceWorker();
  try { await loadConfig(); } catch { /* ignore */ }
  try { await Promise.all([loadMatches(), loadPlayers()]); } catch { toast("Impossibile caricare i dati"); }
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

async function backupDB() {
  try {
    toast("Backup in corso...");
    await fetch("/api/backup");
    toast("Backup completato.");
  } catch {
    toast("Errore nel backup.");
  }
}

async function restoreDB() {
  try {
    toast("Ripristino in corso...");
    await fetch("/api/restore");
    toast("DB ripristinato! Ricarica la pagina.");
    setTimeout(() => location.reload(), 1500);
  } catch {
    toast("Errore nel ripristino.");
  }
}

function closeIconModal() {
  const m = document.getElementById("iconModal");
  if (m) { m.style.display = "none"; m.setAttribute("aria-hidden", "true"); }
}

window.closeIconModal = closeIconModal;

async function openIconPopup(matchId, type) {
  try {
    const m = await api(`/api/matches/${matchId}`);
    const titleEl = document.getElementById("iconModalTitle");
    const bodyEl = document.getElementById("iconModalBody");
    const modal = document.getElementById("iconModal");
    modal.style.display = "block";
    modal.setAttribute("aria-hidden", "false");

    if (type === "convocazioni") {
      titleEl.textContent = "📋 Convocazioni";
      const list = (m.convocations || []).map((c) => c.player ? c.player.name || c.player_id : c.player_id).filter(Boolean);
      bodyEl.innerHTML = list.length ? `<ul style="padding-left:18px;"><li>${list.map((n) => `<strong>${n}</strong>`).join("</li><li>")}</li></ul>` : "<p>Nessun convocato registrato.</p>";
    } else if (type === "indisponibili") {
      titleEl.textContent = "🚫 Indisponibili";
      const list = (m.unavailabilities || []).map((u) => u.player ? u.player.name || u.player_id : u.player_id).filter(Boolean);
      bodyEl.innerHTML = list.length ? `<ul style="padding-left:18px;"><li>${list.map((n) => `<strong>${n}</strong>`).join("</li><li>")}</li></ul>` : "<p>Nessun indisponibile registrato.</p>";
    } else if (type === "passaggi") {
      titleEl.textContent = "🚌 Passaggi / Note";
      const passes = (m.transport || []).map((t) => {
        const driver = t.driver ? (t.driver.name || t.driver_id) : "Autista non specificato";
        return `<strong>${t.kind || "Passaggio"}</strong> — ${driver}, ${t.seats_available || "?"}/${t.seats_total || "?"} posti` + (t.notes ? `<br><span style="font-size:.82rem;color:#777;">Nota: ${t.notes}</span>` : "");
      });
      const notesText = m.notes ? `<p style="margin-top:10px;padding-top:8px;border-top:1px solid #ddd;"><strong>Note gara:</strong> ${m.notes}</p>` : "";
      bodyEl.innerHTML = (passes.length ? `<div>${passes.map((s) => `<p style="margin:4px 0;">${s}</p>`).join("")}</div>` : "<p>Nessun passaggio registrato.</p>") + notesText;
    } else {
      titleEl.textContent = "Dettaglio";
      bodyEl.innerHTML = "<p>Nessun dato disponibile.</p>";
    }
  } catch (e) {
    document.getElementById("iconModalTitle").textContent = "Errore";
    document.getElementById("iconModalBody").innerHTML = "<p>Impossibile caricare i dati.</p>";
    document.getElementById("iconModal").style.display = "block";
  }
}

init();
