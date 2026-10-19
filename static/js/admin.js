/* Area di gestione staff */

const adminData = {
  federations: [],
  teams: [],
  venues: [],
  players: [],
  matches: [],
  unavailability: [],
  convocationStats: {},
  seasonLabel: null,
};
const adminState = { section: "matches", convMatchId: null };

const SECTIONS = [
  ["matches", "Gare"],
  ["convocations", "Convocazioni"],
  ["players", "Giocatori"],
  ["teams", "Squadre"],
  ["venues", "Palestre"],
  ["unavailability", "Indisponibili"],
];

async function loadAdminData() {
  const [federations, teams, venues, players, matches, unavailability, convocationStats, season] = await Promise.all([
    api("/api/federations"),
    api("/api/teams"),
    api("/api/venues"),
    api("/api/players?active_only=false"),
    api("/api/admin/matches"),
    api("/api/availability"),
    api("/api/admin/convocations/stats"),
    api("/api/admin/settings/season"),
  ]);
  Object.assign(adminData, {
    federations, teams, venues, players, matches, unavailability, convocationStats,
    seasonLabel: season.season_label,
  });
}

async function renderAdmin() {
  const box = $("#adminView");
  box.innerHTML = "<p>Caricamento dati gestione…</p>";
  try {
    await loadAdminData();
  } catch {
    box.innerHTML = "<p>Impossibile caricare i dati.</p>";
    return;
  }
  box.innerHTML = "";
  const nav = el("div", "admin-nav");
  SECTIONS.forEach(([key, label]) => {
    const b = el("button", "admin-nav__btn" + (adminState.section === key ? " is-active" : ""), label);
    b.onclick = () => { adminState.section = key; renderAdmin(); };
    nav.appendChild(b);
  });
  box.appendChild(nav);
  const panel = el("div", "admin-panel");
  box.appendChild(panel);
  ({
    matches: renderMatches,
    convocations: renderConvocations,
    players: renderPlayers,
    teams: renderTeams,
    venues: renderVenues,
    unavailability: renderUnavailability,
  }[adminState.section])(panel);
  if (window.refreshPublic) window.refreshPublic();
}

/* ----------------------------- Form helpers --------------------------- */
function fieldWrap(labelText, input) {
  const w = el("label", "field");
  w.appendChild(el("span", "field__label", labelText));
  w.appendChild(input);
  return w;
}
function inputEl(name, value, type = "text") {
  const i = el("input");
  i.name = name;
  i.type = type;
  if (value !== null && value !== undefined) i.value = value;
  return i;
}
function textareaEl(name, value) {
  const t = el("textarea");
  t.name = name;
  t.rows = 3;
  if (value) t.textContent = value;
  return t;
}
function selectEl(name, options, value) {
  const s = el("select");
  s.name = name;
  options.forEach((o) => {
    const opt = el("option", null, o.label);
    opt.value = o.value;
    if (String(o.value) === String(value)) opt.selected = true;
    s.appendChild(opt);
  });
  return s;
}
function checkRow(name, options, selected) {
  const w = el("div", "check-row");
  options.forEach((o) => {
    const l = el("label", "check");
    const c = el("input");
    c.type = "checkbox";
    c.name = name;
    c.value = o.value;
    if (selected.includes(o.value)) c.checked = true;
    l.append(c, el("span", null, o.label));
    w.appendChild(l);
  });
  return w;
}
function adminForm(title, rows, onSubmit) {
  const body = $("#modalBody");
  body.innerHTML = "";
  body.appendChild(el("h2", "detail-title", title));
  const form = el("form", "admin-form");
  rows.forEach((r) => form.appendChild(r));
  const actions = el("div", "form-actions");
  const save = el("button", "btn btn--primary", "Salva");
  save.type = "submit";
  const cancel = el("button", "btn btn--ghost", "Annulla");
  cancel.type = "button";
  cancel.onclick = closeModal;
  actions.append(save, cancel);
  form.appendChild(actions);
  form.onsubmit = async (e) => {
    e.preventDefault();
    try {
      await onSubmit(new FormData(form));
      closeModal();
      await renderAdmin();
    } catch (err) {
      toast("Errore: " + (err.message || err));
    }
  };
  body.appendChild(form);
  openModal();
}
function fedCheckboxes(selectedIds) {
  return checkRow(
    "federation_ids",
    adminData.federations.map((f) => ({ value: f.id, label: f.code })),
    selectedIds || []
  );
}

/* -------------------------------- Gare -------------------------------- */
function renderMatches(panel) {
  const bar = el("div", "admin-toolbar");
  const add = el("button", "btn btn--primary", "+ Nuova gara");
  add.onclick = () => matchForm(null);
  bar.appendChild(add);
  panel.appendChild(bar);

  const list = el("div", "admin-list");
  adminData.matches.forEach((m) => {
    const row = el("div", "admin-row");
    const info = el("div", "admin-row__main");
    info.appendChild(el("div", "admin-row__title", `${m.match_date} · ${fmtTime(m.match_time) || "—"} · ${m.federation.code}`));
    info.appendChild(el("div", "admin-row__sub", `${m.home_team.name} vs ${m.away_team.name}${m.venue ? " · " + m.venue.name : ""}${m.published ? "" : " · NON pubblicata"}`));
    row.appendChild(info);
    const acts = el("div", "admin-row__actions");
    const conv = el("button", "btn btn--sm", "Convocazioni");
    conv.onclick = () => { adminState.section = "convocations"; adminState.convMatchId = m.id; renderAdmin(); };
    const edit = el("button", "btn btn--sm", "Modifica");
    edit.onclick = () => matchForm(m);
    const del = el("button", "btn btn--sm btn--danger", "Elimina");
    del.onclick = () => confirmDelete(`/api/admin/matches/${m.id}`, "Eliminare questa gara?");
    acts.append(conv, edit, del);
    row.appendChild(acts);
    list.appendChild(row);
  });
  panel.appendChild(list);
}

function matchForm(m) {
  const fedOpts = adminData.federations.map((f) => ({ value: f.id, label: f.code }));
  const teamOpts = adminData.teams.map((t) => ({ value: t.id, label: t.name }));
  const venueOpts = [{ value: "", label: "—" }].concat(adminData.venues.map((v) => ({ value: v.id, label: v.name })));
  const rows = [
    fieldWrap("Data", inputEl("match_date", m?.match_date, "date")),
    fieldWrap("Ora", inputEl("match_time", m?.match_time ? fmtTime(m.match_time) : "", "time")),
    fieldWrap("Campionato", selectEl("federation_id", fedOpts, m?.federation.id)),
    fieldWrap("Squadra casa", selectEl("home_team_id", teamOpts, m?.home_team.id)),
    fieldWrap("Squadra ospite", selectEl("away_team_id", teamOpts, m?.away_team.id)),
    fieldWrap("Palestra", selectEl("venue_id", venueOpts, m?.venue?.id ?? "")),
    fieldWrap("Competizione", inputEl("competition", m?.competition)),
    fieldWrap("Giornata", inputEl("matchday", m?.matchday, "number")),
    fieldWrap("Punteggio casa", inputEl("home_score", m?.home_score, "number")),
    fieldWrap("Punteggio ospite", inputEl("away_score", m?.away_score, "number")),
    fieldWrap("Pubblicata (visibile a tutti)", checkRow("published", [{ value: "1", label: "Sì" }], m?.published ? ["1"] : [])),
    fieldWrap("Note", textareaEl("notes", m?.notes)),
  ];
  adminForm(m ? "Modifica gara" : "Nuova gara", rows, async (fd) => {
    const body = {
      match_date: fd.get("match_date"),
      match_time: fd.get("match_time") || null,
      federation_id: intOrNull(fd.get("federation_id")),
      home_team_id: intOrNull(fd.get("home_team_id")),
      away_team_id: intOrNull(fd.get("away_team_id")),
      venue_id: intOrNull(fd.get("venue_id")),
      competition: strOrNull(fd.get("competition")),
      matchday: intOrNull(fd.get("matchday")),
      home_score: intOrNull(fd.get("home_score")),
      away_score: intOrNull(fd.get("away_score")),
      published: fd.get("published") === "1",
      notes: strOrNull(fd.get("notes")),
    };
    await api(m ? `/api/admin/matches/${m.id}` : "/api/admin/matches", {
      method: m ? "PUT" : "POST",
      body: JSON.stringify(body),
    });
    toast("Gara salvata");
  });
}

/* ---------------------------- Convocazioni ---------------------------- */
function renderConvocations(panel) {
  if (!adminData.matches.length) {
    panel.appendChild(el("p", null, "Nessuna gara disponibile."));
    return;
  }
  if (!adminState.convMatchId) adminState.convMatchId = adminData.matches[0].id;
  const match = adminData.matches.find((m) => m.id === adminState.convMatchId);

  const bar = el("div", "admin-toolbar");
  const sel = selectEl(
    "match",
    adminData.matches.map((m) => ({ value: m.id, label: `${m.match_date} · ${m.federation.code} · ${m.home_team.name} vs ${m.away_team.name}` })),
    adminState.convMatchId
  );
  sel.onchange = () => { adminState.convMatchId = intOrNull(sel.value); renderAdmin(); };
  bar.appendChild(fieldWrap("Gara", sel));

  const seasonInput = inputEl("season_label", adminData.seasonLabel || "");
  seasonInput.placeholder = "2026/2027";
  seasonInput.size = 9;
  seasonInput.onchange = async () => {
    const value = seasonInput.value.trim() || null;
    try {
      const saved = await api("/api/admin/settings/season", {
        method: "PUT",
        body: JSON.stringify({ season_label: value }),
      });
      toast(saved.season_label ? `Stagione: ${saved.season_label}` : "Stagione non impostata");
      await renderAdmin();
    } catch {
      toast("Formato non valido (es. 2026/2027)");
    }
  };
  const nextSeason = el("button", "btn btn--sm", "Stagione successiva");
  nextSeason.title = "Passa alla stagione seguente: i conteggi ripartono da zero. Le convocazioni salvate non vengono cancellate.";
  nextSeason.onclick = async () => {
    const m = /^(\d{4})\s*\/\s*(\d{4})$/.exec((adminData.seasonLabel || "").trim());
    let label;
    if (m) {
      label = `${Number(m[1]) + 1}/${Number(m[2]) + 1}`;
    } else {
      const now = new Date();
      const y = now.getMonth() + 1 >= 7 ? now.getFullYear() : now.getFullYear() - 1;
      label = `${y}/${y + 1}`;
    }
    if (!confirm(`Passare alla stagione ${label}? I conteggi ripartiranno da zero; le convocazioni restano salvate.`)) return;
    try {
      await api("/api/admin/settings/season", {
        method: "PUT",
        body: JSON.stringify({ season_label: label }),
      });
      toast(`Stagione impostata: ${label}`);
      await renderAdmin();
    } catch {
      toast("Errore aggiornamento stagione");
    }
  };
  const seasonBox = el("div", "season-box");
  seasonBox.appendChild(el("span", "field__label", "Stagione"));
  seasonBox.appendChild(seasonInput);
  seasonBox.appendChild(nextSeason);
  bar.appendChild(seasonBox);

  panel.appendChild(bar);
  panel.appendChild(el("p", "match-card__meta", "I conteggi considerano le gare della stagione indicata (es. 2026/2027). A fine stagione premi «Stagione successiva» per ripartire da zero: le convocazioni restano salvate."));

  const convBody = el("div", "conv-body");
  panel.appendChild(convBody);
  loadConvocationsEditor(match, convBody);
}

async function loadConvocationsEditor(match, container) {
  container.innerHTML = "<p>Caricamento…</p>";
  let detail;
  try {
    detail = await api(`/api/matches/${match.id}`);
  } catch {
    container.innerHTML = "<p>Impossibile caricare i dati della gara.</p>";
    return;
  }
  const fedCode = match.federation.code;
  const eligible = adminData.players.filter(
    (p) => p.active && (p.federations || []).some((f) => f.code === fedCode)
  );
  const unavailableIds = new Set(
    adminData.unavailability.filter((u) => u.date === match.match_date).map((u) => u.player_id)
  );

  const slots = { starter: new Array(14).fill(null), reserve: new Array(2).fill(null) };
  (detail.convocations || [])
    .filter((c) => !unavailableIds.has(c.player_id))
    .sort((a, b) => (a.slot_order ?? 0) - (b.slot_order ?? 0))
    .forEach((c) => {
      const arr = c.kind === "reserve" ? slots.reserve : slots.starter;
      const idx = arr.indexOf(null);
      if (idx >= 0) arr[idx] = c.player_id;
    });

  container.innerHTML = "";
  const layout = el("div", "conv-layout");

  // Colonna sinistra: giocatori per ruolo
  const left = el("div", "conv-col conv-col--left");
  left.appendChild(el("h4", null, `Giocatori ${fedCode} (${eligible.length})`));
  const byRole = {};
  eligible.forEach((p) => { (byRole[p.role] = byRole[p.role] || []).push(p); });
  Object.keys(byRole).sort().forEach((role) => {
    const grp = el("div", "conv-group");
    grp.appendChild(el("div", "conv-group__title", `Ruolo ${role}`));
    const wrap = el("div", "conv-players");
    byRole[role].forEach((p) => wrap.appendChild(playerPool(p, unavailableIds.has(p.id))));
    grp.appendChild(wrap);
    left.appendChild(grp);
  });
  layout.appendChild(left);

  // Colonna destra: slot
  const right = el("div", "conv-col conv-col--right");
  right.appendChild(el("h4", null, "Convocati (14 + 2 riserve)"));
  right.appendChild(slotGroup("Titolari (14)", "starter", slots.starter));
  right.appendChild(slotGroup("Riserve (2)", "reserve", slots.reserve));
  const save = el("button", "btn btn--primary", "Salva convocazioni");
  save.onclick = async () => {
    const items = [];
    slots.starter.forEach((pid, i) => { if (pid) items.push({ player_id: pid, kind: "starter", slot_order: i }); });
    slots.reserve.forEach((pid, i) => { if (pid) items.push({ player_id: pid, kind: "reserve", slot_order: i }); });
    try {
      await api(`/api/admin/matches/${match.id}/convocations`, { method: "PUT", body: JSON.stringify({ items }) });
      toast("Convocazioni salvate");
      renderAdmin();
    } catch (err) {
      toast("Errore salvataggio");
    }
  };
  right.appendChild(save);
  layout.appendChild(right);
  container.appendChild(layout);

  function playerPool(p, unavailable) {
    const chip = el("div", "pool-chip" + (unavailable ? " is-unavailable" : ""));
    chip.draggable = !unavailable;
    chip.dataset.playerId = p.id;
    chip.appendChild(thumbEl(p, "thumb--xs"));
    chip.appendChild(el("span", "role", p.role2_type || `R${p.role}`));
    chip.appendChild(el("span", null, `${p.first_name} ${p.last_name}`));
    if (unavailable) chip.appendChild(el("span", "flag", "indisp."));
    const st = adminData.convocationStats[p.id] || {};
    const stats = el("span", "pool-chip__stats");
    stats.appendChild(el("span", "pool-stat EISI", `EISI ${st.EISI || 0}`));
    stats.appendChild(el("span", "pool-stat CSAIN", `CSAIN ${st.CSAIN || 0}`));
    chip.appendChild(stats);
    chip.addEventListener("dragstart", (e) => e.dataTransfer.setData("text/plain", String(p.id)));
    return chip;
  }

  function slotGroup(title, kind, arr) {
    const g = el("div", "slots");
    g.appendChild(el("div", "slots__title", title));
    arr.forEach((pid, i) => {
      const slot = el("div", "slot");
      slot.dataset.kind = kind;
      slot.dataset.index = i;
      renderSlotContent(slot, pid);
      slot.addEventListener("dragover", (e) => { e.preventDefault(); slot.classList.add("is-over"); });
      slot.addEventListener("dragleave", () => slot.classList.remove("is-over"));
      slot.addEventListener("drop", (e) => {
        e.preventDefault();
        slot.classList.remove("is-over");
        const playerId = intOrNull(e.dataTransfer.getData("text/plain"));
        if (!playerId) return;
        // rimuovi il giocatore da eventuali altri slot
        ["starter", "reserve"].forEach((k) => {
          const idx = slots[k].indexOf(playerId);
          if (idx >= 0) {
            slots[k][idx] = null;
            const other = container.querySelector(`.slot[data-kind="${k}"][data-index="${idx}"]`);
            if (other) renderSlotContent(other, null);
          }
        });
        arr[i] = playerId;
        renderSlotContent(slot, playerId);
      });
      g.appendChild(slot);
    });
    return g;
  }

  function renderSlotContent(slot, pid) {
    slot.innerHTML = "";
    if (!pid) {
      slot.classList.remove("is-filled");
      slot.appendChild(el("span", "slot__empty", "Trascina qui"));
      return;
    }
    const p = adminData.players.find((x) => x.id === pid);
    slot.classList.add("is-filled");
    if (p) slot.appendChild(thumbEl(p, "thumb--xs"));
    slot.appendChild(el("span", "role", p?.role2_type || `R${p?.role}`));
    slot.appendChild(el("span", "slot__name", p ? `${p.first_name} ${p.last_name}` : `#${pid}`));
    const x = el("button", "slot__remove", "✕");
    x.onclick = () => {
      const k = slot.dataset.kind;
      slots[k][intOrNull(slot.dataset.index)] = null;
      renderSlotContent(slot, null);
    };
    slot.appendChild(x);
  }
}

/* ------------------------------- Giocatori ---------------------------- */
function renderPlayers(panel) {
  const bar = el("div", "admin-toolbar");
  const add = el("button", "btn btn--primary", "+ Nuovo giocatore");
  add.onclick = () => playerForm(null);
  bar.appendChild(add);
  panel.appendChild(bar);

  const byRole = {};
  adminData.players.forEach((p) => {
    (byRole[p.role] = byRole[p.role] || []).push(p);
  });
  Object.keys(byRole).sort((a, b) => a - b).forEach((role) => {
    panel.appendChild(el("h3", "admin-group-title", `Ruolo ${role} (${byRole[role].length})`));
    const list = el("div", "admin-list");
    byRole[role].forEach((p) => list.appendChild(playerRow(p)));
    panel.appendChild(list);
  });
}

function playerRow(p) {
  const row = el("div", "admin-row" + (p.active ? "" : " is-inactive"));
  row.appendChild(thumbEl(p, "thumb--sm"));
  const main = el("div", "admin-row__main");
  const fedCodes = (p.federations || []).map((f) => f.code).join(", ") || "nessuna";
  const title = el("div", "admin-row__title");
  title.appendChild(el("span", null, `${p.role2_type || "R" + p.role} · ${p.first_name} ${p.last_name}`));
  if (!p.active) title.appendChild(el("span", "pill inactive", "non attivo"));
  main.appendChild(title);
  let sub = `Iscritto: ${fedCodes}`;
  if (p.role === 1 && p.shot_distance_cm) sub += ` · Tiro: ${p.shot_distance_cm} cm`;
  main.appendChild(el("div", "admin-row__sub", sub));
  row.appendChild(main);
  const acts = el("div", "admin-row__actions");
  const toggle = el("button", "btn btn--sm" + (p.active ? "" : " btn--primary"), p.active ? "Disattiva" : "Attiva");
  toggle.onclick = () => setPlayerActive(p, !p.active);
  const edit = el("button", "btn btn--sm", "Modifica");
  edit.onclick = () => playerForm(p);
  const del = el("button", "btn btn--sm btn--danger", "Elimina");
  del.onclick = () => confirmDelete(`/api/admin/players/${p.id}`, `Eliminare ${p.first_name} ${p.last_name}?`);
  acts.append(toggle, edit, del);
  row.appendChild(acts);
  return row;
}

function playerForm(p) {
  const roleOpts = [1, 2, 3, 4, 5, 6].map((r) => ({ value: r, label: `Ruolo ${r}` }));
  const typeOpts = [
    { value: "", label: "— (solo per ruolo 2)" },
    { value: "2P", label: "2P" },
    { value: "2T", label: "2T" },
    { value: "2R", label: "2R" },
  ];
  const roleSelect = selectEl("role", roleOpts, p?.role ?? 1);
  const subtypeWrap = fieldWrap("Sottotipo ruolo 2", selectEl("role2_type", typeOpts, p?.role2_type ?? ""));
  const shotInput = inputEl("shot_distance_cm", p?.shot_distance_cm ?? "", "number");
  shotInput.min = "1";
  shotInput.placeholder = "es. 300";
  const shotWrap = fieldWrap("Distanza di tiro (cm)", shotInput);
  const updateRoleFields = () => {
    const role = Number(roleSelect.value);
    subtypeWrap.style.display = role === 2 ? "" : "none";
    shotWrap.style.display = role === 1 ? "" : "none";
  };
  roleSelect.onchange = updateRoleFields;
  const rows = [
    fieldWrap("Nome", inputEl("first_name", p?.first_name)),
    fieldWrap("Cognome", inputEl("last_name", p?.last_name)),
    fieldWrap("Ruolo", roleSelect),
    subtypeWrap,
    shotWrap,
    fieldWrap("Foto (URL)", inputEl("photo_url", p?.photo_url)),
    fieldWrap("Codice EISI", inputEl("code_eisi", p?.code_eisi)),
    fieldWrap("Codice CSAIN", inputEl("code_csain", p?.code_csain)),
    fieldWrap("Email", inputEl("email", p?.email)),
    fieldWrap("Telefono", inputEl("phone", p?.phone)),
    fieldWrap("Attivo", checkRow("active", [{ value: "1", label: "Sì" }], p ? (p.active ? ["1"] : []) : ["1"])),
    fieldWrap("Campionati (iscrizione)", fedCheckboxes((p?.federations || []).map((f) => f.id))),
  ];
  updateRoleFields();
  adminForm(p ? "Modifica giocatore" : "Nuovo giocatore", rows, async (fd) => {
    const role = intOrNull(fd.get("role"));
    const body = {
      first_name: fd.get("first_name"),
      last_name: fd.get("last_name"),
      role,
      role2_type: role === 2 ? strOrNull(fd.get("role2_type")) : null,
      shot_distance_cm: role === 1 ? intOrNull(fd.get("shot_distance_cm")) : null,
      photo_url: strOrNull(fd.get("photo_url")),
      code_eisi: strOrNull(fd.get("code_eisi")),
      code_csain: strOrNull(fd.get("code_csain")),
      email: strOrNull(fd.get("email")),
      phone: strOrNull(fd.get("phone")),
      active: fd.get("active") === "1",
      federation_ids: fd.getAll("federation_ids").map(Number),
    };
    await api(p ? `/api/admin/players/${p.id}` : "/api/admin/players", {
      method: p ? "PUT" : "POST",
      body: JSON.stringify(body),
    });
    toast("Giocatore salvato");
  });
}

/* -------------------------------- Squadre ----------------------------- */
function renderTeams(panel) {
  const bar = el("div", "admin-toolbar");
  const add = el("button", "btn btn--primary", "+ Nuova squadra");
  add.onclick = () => teamForm(null);
  bar.appendChild(add);
  panel.appendChild(bar);

  const list = el("div", "admin-list");
  adminData.teams.forEach((t) => {
    const row = el("div", "admin-row");
    const logo = logoThumbEl(t, "thumb--sm");
    if (logo) row.appendChild(logo);
    const main = el("div", "admin-row__main");
    main.appendChild(el("div", "admin-row__title", `${t.name}${t.is_ours ? " ⭐" : ""}`));
    main.appendChild(el("div", "admin-row__sub", `${t.city || "—"} · ${(t.federations || []).map((f) => f.code).join(", ") || "nessun campionato"}`));
    row.appendChild(main);
    const acts = el("div", "admin-row__actions");
    const edit = el("button", "btn btn--sm", "Modifica");
    edit.onclick = () => teamForm(t);
    const del = el("button", "btn btn--sm btn--danger", "Elimina");
    del.onclick = () => confirmDelete(`/api/admin/teams/${t.id}`, `Eliminare ${t.name}?`);
    acts.append(edit, del);
    row.appendChild(acts);
    list.appendChild(row);
  });
  panel.appendChild(list);
}

function teamForm(t) {
  const logoInput = inputEl("logo_url", t?.logo_url);
  const preview = el("div", "logo-preview");
  const previewImg = el("img", "thumb thumb--logo thumb--lg");
  previewImg.alt = t?.name || "Anteprima logo";
  previewImg.referrerPolicy = "no-referrer";
  previewImg.style.display = "none";
  previewImg.onload = () => { previewImg.style.display = ""; };
  previewImg.onerror = () => { previewImg.style.display = "none"; };
  preview.appendChild(previewImg);
  const updatePreview = () => {
    const v = (logoInput.value || "").trim();
    if (v) { previewImg.src = v; } else { previewImg.removeAttribute("src"); previewImg.style.display = "none"; }
  };
  logoInput.addEventListener("input", updatePreview);
  updatePreview();

  const rows = [
    fieldWrap("Nome", inputEl("name", t?.name)),
    fieldWrap("Città", inputEl("city", t?.city)),
    fieldWrap("Logo (URL)", logoInput),
    fieldWrap("Anteprima logo", preview),
    fieldWrap("È la nostra squadra", checkRow("is_ours", [{ value: "1", label: "Sì" }], t?.is_ours ? ["1"] : [])),
    fieldWrap("Campionati", fedCheckboxes((t?.federations || []).map((f) => f.id))),
  ];
  adminForm(t ? "Modifica squadra" : "Nuova squadra", rows, async (fd) => {
    const body = {
      name: fd.get("name"),
      city: strOrNull(fd.get("city")),
      logo_url: strOrNull(fd.get("logo_url")),
      is_ours: fd.get("is_ours") === "1",
      federation_ids: fd.getAll("federation_ids").map(Number),
    };
    await api(t ? `/api/admin/teams/${t.id}` : "/api/admin/teams", {
      method: t ? "PUT" : "POST",
      body: JSON.stringify(body),
    });
    toast("Squadra salvata");
  });
}

/* -------------------------------- Palestre ---------------------------- */
function renderVenues(panel) {
  const bar = el("div", "admin-toolbar");
  const add = el("button", "btn btn--primary", "+ Nuova palestra");
  add.onclick = () => venueForm(null);
  bar.appendChild(add);
  panel.appendChild(bar);

  const list = el("div", "admin-list");
  adminData.venues.forEach((v) => {
    const row = el("div", "admin-row");
    const main = el("div", "admin-row__main");
    main.appendChild(el("div", "admin-row__title", v.name));
    main.appendChild(el("div", "admin-row__sub", v.address || "—"));
    const teams = v.teams || [];
    if (teams.length) {
      const chips = el("div", "venue-teams");
      teams.forEach((t) => {
        const chip = el("span", "venue-team");
        chip.appendChild(logoThumbEl(t, "thumb--xs"));
        chip.appendChild(el("span", null, t.name));
        chips.appendChild(chip);
      });
      main.appendChild(chips);
    } else {
      main.appendChild(el("div", "admin-row__sub", "Nessuna squadra associata"));
    }
    row.appendChild(main);
    const acts = el("div", "admin-row__actions");
    const edit = el("button", "btn btn--sm", "Modifica");
    edit.onclick = () => venueForm(v);
    const del = el("button", "btn btn--sm btn--danger", "Elimina");
    del.onclick = () => confirmDelete(`/api/admin/venues/${v.id}`, `Eliminare ${v.name}?`);
    acts.append(edit, del);
    row.appendChild(acts);
    list.appendChild(row);
  });
  panel.appendChild(list);
}

function venueForm(v) {
  const selected = (v?.teams || []).map((t) => t.id);
  const teamOpts = adminData.teams
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((t) => ({ value: t.id, label: t.name }));
  const teamChecks = checkRow("team_ids", teamOpts, selected);
  teamChecks.classList.add("check-row--scroll");
  const rows = [
    fieldWrap("Nome", inputEl("name", v?.name)),
    fieldWrap("Indirizzo", inputEl("address", v?.address)),
    fieldWrap("Link Google Maps", inputEl("maps_url", v?.maps_url)),
    fieldWrap("Squadre che giocano qui", teamChecks),
  ];
  adminForm(v ? "Modifica palestra" : "Nuova palestra", rows, async (fd) => {
    const body = {
      name: fd.get("name"),
      address: strOrNull(fd.get("address")),
      maps_url: strOrNull(fd.get("maps_url")),
      team_ids: fd.getAll("team_ids").map(Number),
    };
    await api(v ? `/api/admin/venues/${v.id}` : "/api/admin/venues", {
      method: v ? "PUT" : "POST",
      body: JSON.stringify(body),
    });
    toast("Palestra salvata");
  });
}

/* ----------------------------- Indisponibili ------------------------- */
function renderUnavailability(panel) {
  const bar = el("div", "admin-toolbar");
  const add = el("button", "btn btn--primary", "+ Nuova indisponibilità");
  add.onclick = () => unavailabilityForm();
  bar.appendChild(add);
  panel.appendChild(bar);

  const list = el("div", "admin-list");
  adminData.unavailability.forEach((u) => {
    const row = el("div", "admin-row");
    const main = el("div", "admin-row__main");
    main.appendChild(el("div", "admin-row__title", `${u.player.first_name} ${u.player.last_name}`));
    main.appendChild(el("div", "admin-row__sub", `${u.date}${u.reason ? " · " + u.reason : ""}`));
    row.appendChild(main);
    const acts = el("div", "admin-row__actions");
    const del = el("button", "btn btn--sm btn--danger", "Elimina");
    del.onclick = () => confirmDelete(`/api/admin/unavailability/${u.id}`, "Eliminare questa indisponibilità?");
    acts.appendChild(del);
    row.appendChild(acts);
    list.appendChild(row);
  });
  panel.appendChild(list);
}

const MONTHS_IT = [
  "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
  "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
];

function unavailabilityForm() {
  const playerOpts = adminData.players
    .filter((p) => p.active)
    .map((p) => ({ value: p.id, label: `${p.first_name} ${p.last_name}` }));
  const matches = adminData.matches
    .slice()
    .sort((a, b) => a.match_date.localeCompare(b.match_date));
  const years = [...new Set(matches.map((m) => m.match_date.slice(0, 4)))].sort();

  const now = new Date();
  const todayIso = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const nextMatch = matches.find((m) => m.match_date >= todayIso) || matches[0];
  const defaultYear = nextMatch ? nextMatch.match_date.slice(0, 4) : String(now.getFullYear());
  const defaultMonth = nextMatch ? nextMatch.match_date.slice(5, 7) : "";

  const yearSel = selectEl("match_year", years.map((y) => ({ value: y, label: y })), defaultYear);
  const monthOpts = [{ value: "", label: "Tutti i mesi" }].concat(
    MONTHS_IT.map((n, i) => ({ value: pad(i + 1), label: n }))
  );
  const monthSel = selectEl("match_month", monthOpts, defaultMonth);
  const matchSel = selectEl("match_id", [], "");
  const matchHint = el("p", "match-card__meta");

  const fillMatches = () => {
    const y = yearSel.value;
    const mo = monthSel.value;
    const list = matches.filter(
      (m) => m.match_date.slice(0, 4) === y && (!mo || m.match_date.slice(5, 7) === mo)
    );
    matchSel.innerHTML = "";
    if (!list.length) {
      const o = el("option", null, "Nessuna gara in questo periodo");
      o.value = "";
      matchSel.appendChild(o);
      matchSel.disabled = true;
      matchHint.textContent = "Cambia anno/mese oppure aggiungi prima una gara nel calendario.";
      return;
    }
    matchSel.disabled = false;
    list.forEach((m) => {
      const o = el("option", null, `${m.match_date} · ${m.federation.code} · ${m.home_team.name} vs ${m.away_team.name}`);
      o.value = m.id;
      matchSel.appendChild(o);
    });
    matchHint.textContent = `${list.length} gara/e nel periodo selezionato. La data viene compilata dalla gara scelta.`;
  };
  yearSel.onchange = fillMatches;
  monthSel.onchange = fillMatches;
  fillMatches();

  const rows = [
    fieldWrap("Giocatore", selectEl("player_id", playerOpts, playerOpts[0]?.value)),
    fieldWrap("Anno", yearSel),
    fieldWrap("Mese", monthSel),
    fieldWrap("Gara", matchSel),
    matchHint,
    fieldWrap("Motivo", inputEl("reason", "")),
  ];
  adminForm("Nuova indisponibilità", rows, async (fd) => {
    const match = matches.find((m) => String(m.id) === String(fd.get("match_id")));
    if (!match) throw new Error("Seleziona una gara");
    const body = {
      player_id: intOrNull(fd.get("player_id")),
      date: match.match_date,
      reason: strOrNull(fd.get("reason")),
    };
    await api("/api/admin/unavailability", { method: "POST", body: JSON.stringify(body) });
    toast(`Indisponibilità salvata per il ${match.match_date}`);
  });
}

/* -------------------------------- Utils ------------------------------- */
function thumbEl(p, cls) {
  const name = p ? `${p.first_name} ${p.last_name}` : "?";
  if (p && p.photo_url) {
    const img = el("img", "thumb " + (cls || ""));
    img.src = p.photo_url;
    img.alt = name;
    img.loading = "lazy";
    img.referrerPolicy = "no-referrer";
    img.onerror = () => img.replaceWith(thumbFallback(name, cls));
    return img;
  }
  return thumbFallback(name, cls);
}
function thumbFallback(name, cls) {
  return el("span", "thumb thumb--fallback " + (cls || ""), initials(name));
}
function logoThumbEl(t, cls) {
  const name = t ? t.name : "?";
  if (t && t.logo_url) {
    const img = el("img", "thumb thumb--logo " + (cls || ""));
    img.src = t.logo_url;
    img.alt = name;
    img.loading = "lazy";
    img.referrerPolicy = "no-referrer";
    img.onerror = () => img.replaceWith(teamFallback(name, cls));
    return img;
  }
  return teamFallback(name, cls);
}
function teamFallback(name, cls) {
  const ini = name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  return el("span", "thumb thumb--logo thumb--fallback " + (cls || ""), ini);
}
async function setPlayerActive(p, active) {
  const body = {
    first_name: p.first_name,
    last_name: p.last_name,
    role: p.role,
    role2_type: p.role2_type,
    shot_distance_cm: p.shot_distance_cm,
    photo_url: p.photo_url,
    code_eisi: p.code_eisi,
    code_csain: p.code_csain,
    email: p.email,
    phone: p.phone,
    active,
    federation_ids: (p.federations || []).map((f) => f.id),
  };
  try {
    await api(`/api/admin/players/${p.id}`, { method: "PUT", body: JSON.stringify(body) });
    toast(active ? "Giocatore attivato" : "Giocatore disattivato");
    await renderAdmin();
  } catch {
    toast("Errore durante l'aggiornamento");
  }
}
function intOrNull(v) {
  if (v === null || v === undefined || v === "") return null;
  const n = parseInt(v, 10);
  return Number.isNaN(n) ? null : n;
}
function strOrNull(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return s === "" ? null : s;
}
async function confirmDelete(path, message) {
  if (!confirm(message)) return;
  try {
    await api(path, { method: "DELETE" });
    toast("Eliminato");
    await renderAdmin();
  } catch {
    toast("Errore durante l'eliminazione");
  }
}

window.renderAdmin = renderAdmin;
