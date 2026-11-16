/* ==========================================================================
   Referti & statistiche CarpeDiem
   Pannello staff: referti gara in stile Excel, statistiche squadra e giocatori.
   Pagina standalone (/referti): usa solo gli helper globali state e toast
   definiti da referti.js.
   ========================================================================== */
(() => {
  "use strict";

  const R = {
    loaded: false,
    loading: false,
    error: null,
    section: "dashboard",
    board: null,
    stats: null,
    statsLoading: false,
    season: null,
    federation: "",
    filters: { opponent_id: "", venue: "", result: "", include_drafts: false },
    matchFilter: "all",
    search: "",
    playerSort: "points",
    playerFed: "",
    playerSearch: "",
    playerId: null,
    playerDetail: null,
    playerLoading: false,
    editor: null,
    import: null,
  };

  const h = (tag, cls, html) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html !== undefined) node.innerHTML = html;
    return node;
  };

  const esc = (value) =>
    String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const clampInt = (value) => {
    const n = parseInt(value, 10);
    return Number.isFinite(n) && n > 0 ? n : 0;
  };

  const num = (value, digits = 1) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return "0";
    return String(Math.round(n * 10 ** digits) / 10 ** digits);
  };

  const plural = (count, one, many) => `${count} ${Number(count) === 1 ? one : many}`;

  const initialsOf = (name) =>
    String(name || "")
      .split(/\s+/)
      .filter(Boolean)
      .map((word) => word[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();

  const titleCase = (value) =>
    String(value || "")
      .toLocaleLowerCase("it-IT")
      .replace(/(^|[\s'’\-])([a-zà-ÿ])/g, (_, prefix, letter) => prefix + letter.toLocaleUpperCase("it-IT"));

  const shortDate = (iso) => {
    if (!iso) return "";
    const d = new Date(String(iso).slice(0, 10) + "T12:00:00");
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric" });
  };

  const shortDateNoYear = (iso) => {
    if (!iso) return "";
    const d = new Date(String(iso).slice(0, 10) + "T12:00:00");
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit" });
  };

  const resultBadge = (result) => {
    if (result === "W") return '<span class="rp-badge rp-badge--win">Vittoria</span>';
    if (result === "L") return '<span class="rp-badge rp-badge--loss">Sconfitta</span>';
    if (result === "D") return '<span class="rp-badge rp-badge--draw">Pareggio</span>';
    return '<span class="rp-badge rp-badge--muted">—</span>';
  };

  const resultLetter = (result) => (result === "W" ? "V" : result === "L" ? "S" : result === "D" ? "P" : "—");

  const fedPill = (code) =>
    code ? `<span class="rp-pill-fed ${esc(code)}">${esc(code)}</span>` : "";

  async function rApi(path, opts = {}) {
    const headers = { ...(opts.headers || {}) };
    if (!(opts.body instanceof FormData)) headers["Content-Type"] = "application/json";
    const res = await fetch((window.CarpeDiemAPI || "") + path, { ...opts, headers });
    if (!res.ok) {
      let detail = "";
      try {
        const data = await res.json();
        detail = data.detail || data.message || "";
      } catch {
        /* risposta non JSON */
      }
      const error = new Error(detail || `Errore ${res.status}`);
      error.status = res.status;
      throw error;
    }
    return res.status === 204 ? null : res.json();
  }

  function errorBox(error) {
    const needLogin = error && error.status === 401;
    return `<div class="rp-empty">
      <div class="rp-empty__icon">${needLogin ? "🔒" : "⚠️"}</div>
      <strong>${needLogin ? "Sessione staff scaduta" : "Impossibile caricare i referti"}</strong>
      <p>${needLogin ? "Accedi di nuovo per continuare a consultare referti e statistiche." : esc(error?.message || "Riprova tra poco.")}</p>
      ${needLogin
        ? '<button class="rp-btn rp-btn--primary" data-rp-login>Accedi</button>'
        : '<button class="rp-btn rp-btn--primary" data-rp-retry>Riprova</button>'}
    </div>`;
  }

  function emptyBox(icon, title, text, actionLabel, actionAttr) {
    return `<div class="rp-empty">
      <div class="rp-empty__icon">${icon}</div>
      <strong>${esc(title)}</strong>
      <p>${esc(text)}</p>
      ${actionLabel ? `<button class="rp-btn rp-btn--primary" ${actionAttr}>${esc(actionLabel)}</button>` : ""}
    </div>`;
  }

  function qs(params = {}) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== "" && value !== null && value !== undefined && value !== false) {
        search.set(key, String(value));
      }
    });
    const text = search.toString();
    return text ? `?${text}` : "";
  }

  /* ------------------------------- Charts -------------------------------- */

  function lineChart(rows, opts = {}) {
    const width = 680;
    const height = opts.height || 230;
    const pad = { top: 16, right: 14, bottom: 30, left: 34 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;
    const values = rows.flatMap((row) => [row.our_score || 0, row.opp_score || 0]);
    const maxValue = Math.max(10, ...values);
    const step = Math.max(5, Math.ceil(maxValue / 4 / 5) * 5);
    const top = step * 4;
    const x = (index) =>
      pad.left + (rows.length <= 1 ? plotW / 2 : (index / (rows.length - 1)) * plotW);
    const y = (value) => pad.top + plotH - (value / top) * plotH;
    const points = (key) => rows.map((row, index) => `${x(index)},${y(row[key] || 0)}`).join(" ");

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("class", "rp-chart");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", opts.label || "Andamento punteggio");

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.innerHTML = `<linearGradient id="rpAreaGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f58220" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#f58220" stop-opacity="0"/>
    </linearGradient>`;
    svg.appendChild(defs);

    for (let i = 0; i <= 4; i++) {
      const value = (step * i);
      const yy = y(value);
      const grid = document.createElementNS("http://www.w3.org/2000/svg", "line");
      grid.setAttribute("x1", pad.left);
      grid.setAttribute("x2", width - pad.right);
      grid.setAttribute("y1", yy);
      grid.setAttribute("y2", yy);
      grid.setAttribute("class", "rp-gridline");
      svg.appendChild(grid);
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", pad.left - 7);
      label.setAttribute("y", yy + 3);
      label.setAttribute("text-anchor", "end");
      label.textContent = String(value);
      svg.appendChild(label);
    }

    if (rows.length > 1) {
      const area = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
      area.setAttribute("class", "rp-area");
      area.setAttribute("points", `${pad.left},${y(0)} ${points("our_score")} ${x(rows.length - 1)},${y(0)}`);
      svg.appendChild(area);

      const oppLine = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      oppLine.setAttribute("class", "rp-line-opp");
      oppLine.setAttribute("points", points("opp_score"));
      svg.appendChild(oppLine);

      const ourLine = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
      ourLine.setAttribute("class", "rp-line-ours");
      ourLine.setAttribute("points", points("our_score"));
      svg.appendChild(ourLine);
    }

    const labelEvery = Math.max(1, Math.ceil(rows.length / 7));
    rows.forEach((row, index) => {
      const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("class", "rp-dot-ours");
      dot.setAttribute("cx", x(index));
      dot.setAttribute("cy", y(row.our_score || 0));
      dot.setAttribute("r", 3.5);
      dot.innerHTML = `<title>${esc(shortDate(row.date))} · ${esc(row.opponent)}: ${row.our_score}-${row.opp_score}</title>`;
      svg.appendChild(dot);

      if (index % labelEvery === 0 || index === rows.length - 1) {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", x(index));
        label.setAttribute("y", height - 9);
        label.setAttribute("text-anchor", "middle");
        label.textContent = shortDateNoYear(row.date);
        svg.appendChild(label);
      }
    });

    return svg;
  }

  function quarterBars(ours, opp) {
    const box = h("div", "rp-bars");
    const maxValue = Math.max(1, ...ours, ...opp);
    ["1Q", "2Q", "3Q", "4Q"].forEach((label, index) => {
      const col = h("div", "rp-bars__col");
      const pair = h("div", "rp-bars__pair");
      const mk = (value, cls, title) => {
        const bar = h("div", `rp-bars__bar ${cls}`);
        bar.style.height = `${Math.max(2, Math.round((value / maxValue) * 150))}px`;
        bar.title = title;
        return bar;
      };
      pair.appendChild(mk(ours[index] || 0, "rp-bars__bar--ours", `CarpeDiem ${ours[index] || 0}`));
      pair.appendChild(mk(opp[index] || 0, "rp-bars__bar--opp", `Avversari ${opp[index] || 0}`));
      col.appendChild(pair);
      col.appendChild(h("span", "rp-bars__value", `${ours[index] || 0} - ${opp[index] || 0}`));
      col.appendChild(h("span", "rp-bars__label", label));
      box.appendChild(col);
    });
    return box;
  }

  function legend(oursLabel = "CarpeDiem", oppLabel = "Avversari") {
    return `<div class="rp-legend">
      <span><i style="background:#f58220"></i>${esc(oursLabel)}</span>
      <span><i style="background:#5c6a7d"></i>${esc(oppLabel)}</span>
    </div>`;
  }

  function miniQuarters(values) {
    const max = Math.max(1, ...values);
    return `<span class="rp-mini">${values
      .map((value) => `<i style="height:${Math.max(2, Math.round((value / max) * 18))}px" title="${value} punti"></i>`)
      .join("")}</span>`;
  }

  /* ------------------------------ Loaders -------------------------------- */

  function seasonQuery() {
    return qs({ season: R.season || "", federation: R.federation || "" });
  }

  async function loadBoard(force = false) {
    if (R.loading) return;
    R.loading = true;
    R.error = null;
    try {
      R.board = await rApi(`/api/admin/reports/board${seasonQuery()}`);
      R.season = R.board.season_label || R.season;
      if (!R.board.seasons.includes(R.season)) R.board.seasons.push(R.season);
      R.loaded = true;
      R.stats = null;
    } catch (error) {
      R.error = error;
    } finally {
      R.loading = false;
    }
  }

  async function loadStats(force = false) {
    if (R.statsLoading) return;
    if (R.stats && !force) return;
    R.statsLoading = true;
    try {
      const f = R.filters;
      R.stats = await rApi(
        `/api/admin/reports/stats${qs({
          season: R.season || "",
          federation: R.federation || "",
          opponent_id: f.opponent_id,
          venue: f.venue,
          result: f.result,
          include_drafts: f.include_drafts,
        })}`
      );
    } catch (error) {
      R.error = error;
    } finally {
      R.statsLoading = false;
    }
  }

  function rpRender() {
    const box = document.getElementById("reportsView");
    if (!box) return;
    box.innerHTML = "";
    if (!state.isStaff) {
      box.innerHTML = `<div class="rp">${errorBox({ status: 401 })}</div>`;
      return;
    }
    if (R.loading && !R.board) {
      box.innerHTML = `<div class="rp"><div class="rp-skeleton">
        <div class="rp-skel" style="height:150px"></div>
        <div class="rp-skel" style="width:60%"></div>
        <div class="rp-skel" style="height:90px"></div>
        <div class="rp-skel" style="height:220px"></div>
      </div></div>`;
      return;
    }
    if (R.error && !R.board) {
      box.innerHTML = `<div class="rp">${errorBox(R.error)}</div>`;
      return;
    }

    const shell = h("div", "rp");
    if (!R.editor) shell.appendChild(heroNode());

    if (R.editor) {
      shell.appendChild(editorNode());
      box.appendChild(shell);
      return;
    }

    shell.appendChild(tabsNode());
    const body = h("div");
    shell.appendChild(body);
    box.appendChild(shell);

    if (R.section === "dashboard") renderDashboard(body);
    else if (R.section === "matches") renderMatches(body);
    else if (R.section === "players") renderPlayers(body);
    else if (R.section === "opponents") renderOpponents(body);
  }

  function heroNode() {
    const board = R.board || {};
    const hero = h("div", "rp-hero");
    const copy = h("div");
    copy.appendChild(h("div", "rp-eyebrow", "Area staff · CarpeDiem Baskin"));
    copy.appendChild(h("h1", null, "Referti & statistiche"));
    copy.appendChild(
      h("p", null, `${board.our_team?.name || "CarpeDiem"} · stagione ${esc(board.season_label || R.season || "—")} · dati calcolati dai referti definitivi`)
    );
    hero.appendChild(copy);

    const seasonBox = h("div", "rp-hero__season");
    seasonBox.appendChild(h("label", null, "Stagione"));
    const select = h("select");
    (board.seasons || []).forEach((season) => {
      const option = h("option", null, esc(season));
      option.value = season;
      option.selected = season === R.season;
      select.appendChild(option);
    });
    select.onchange = async () => {
      R.season = select.value;
      R.loaded = false;
      R.playerDetail = null;
      await loadBoard(true);
      await loadStats(true);
      rpRender();
    };
    seasonBox.appendChild(select);
    hero.appendChild(seasonBox);
    return hero;
  }

  function tabsNode() {
    const tabs = h("div", "rp-tabs");
    const items = [
      ["dashboard", "Dashboard"],
      ["matches", "Partite & referti"],
      ["players", "Giocatori"],
      ["opponents", "Avversari"],
    ];
    items.forEach(([key, label]) => {
      const button = h("button", "rp-tab" + (R.section === key ? " is-active" : ""), label);
      button.onclick = () => {
        R.section = key;
        R.playerId = null;
        R.playerDetail = null;
        if (key === "dashboard" || key === "players" || key === "opponents") loadStats();
        rpRender();
      };
      tabs.appendChild(button);
    });

    const spacer = h("div", "rp-spacer");
    tabs.appendChild(spacer);

    const fed = h("div", "rp-row");
    const all = h("button", "rp-tab" + (!R.federation ? " is-active" : ""), "Tutte");
    all.onclick = () => setFederation("");
    fed.appendChild(all);
    ["EISI", "CSAIN"].forEach((code) => {
      const button = h("button", "rp-tab" + (R.federation === code ? " is-active" : ""), code);
      button.onclick = () => setFederation(code);
      fed.appendChild(button);
    });
    tabs.appendChild(fed);
    return tabs;
  }

  async function setFederation(code) {
    if (R.federation === code) return;
    R.federation = code;
    R.loaded = false;
    R.playerDetail = null;
    await loadBoard(true);
    await loadStats(true);
    rpRender();
  }

  /* ------------------------------ Dashboard ------------------------------ */

  function filterRow(onChange) {
    const row = h("div", "rp-filterbar");
    row.appendChild(h("span", "rp-hint", "Filtri statistiche"));

    const opponent = h("select");
    const all = h("option", null, "Tutti gli avversari");
    all.value = "";
    opponent.appendChild(all);
    (R.board?.opponents || []).forEach((team) => {
      const option = h("option", null, esc(team.name));
      option.value = String(team.id);
      option.selected = String(R.filters.opponent_id) === String(team.id);
      opponent.appendChild(option);
    });
    opponent.onchange = () => {
      R.filters.opponent_id = opponent.value;
      onChange();
    };
    row.appendChild(opponent);

    const venue = h("select");
    [["", "Casa e trasferta"], ["home", "Solo in casa"], ["away", "Solo in trasferta"]].forEach(([value, label]) => {
      const option = h("option", null, label);
      option.value = value;
      option.selected = R.filters.venue === value;
      venue.appendChild(option);
    });
    venue.onchange = () => {
      R.filters.venue = venue.value;
      onChange();
    };
    row.appendChild(venue);

    const result = h("select");
    [["", "Tutti i risultati"], ["W", "Vittorie"], ["L", "Sconfitte"], ["D", "Pareggi"]].forEach(([value, label]) => {
      const option = h("option", null, label);
      option.value = value;
      option.selected = R.filters.result === value;
      result.appendChild(option);
    });
    result.onchange = () => {
      R.filters.result = result.value;
      onChange();
    };
    row.appendChild(result);

    const draft = h("label", "rp-hint");
    draft.style.display = "inline-flex";
    draft.style.alignItems = "center";
    draft.style.gap = "6px";
    const check = h("input");
    check.type = "checkbox";
    check.checked = R.filters.include_drafts;
    check.onchange = () => {
      R.filters.include_drafts = check.checked;
      onChange();
    };
    draft.appendChild(check);
    draft.appendChild(document.createTextNode("Includi bozze"));
    row.appendChild(draft);
    return row;
  }

  function renderDashboard(box) {
    const wrap = h("div", "rp-stack");
    const syncButton = h("button", "rp-btn rp-btn--soft", "⟳ Sincronizza calendario");
    syncButton.onclick = () => syncPublic(syncButton);

    const head = h("div", "rp-row rp-row--between");
    head.appendChild(h("div", "rp-card__title", "Panoramica squadra"));
    const headActions = h("div", "rp-row");
    headActions.appendChild(syncButton);
    head.appendChild(headActions);
    wrap.appendChild(head);

    wrap.appendChild(filterRow(async () => {
      await loadStats(true);
      rpRender();
    }));

    if (!R.stats) {
      const loading = h("div", "rp-skeleton");
      loading.innerHTML = '<div class="rp-skel" style="height:100px"></div><div class="rp-skel" style="height:220px"></div>';
      wrap.appendChild(loading);
      box.appendChild(wrap);
      loadStats().then(() => rpRender());
      return;
    }

    const s = R.stats.summary || {};
    const kpis = h("div", "rp-grid rp-grid--kpi");
    const kpi = (label, value, hint, accent) => {
      const card = h("div", "rp-kpi" + (accent ? " rp-kpi--accent" : ""));
      card.appendChild(h("span", "rp-kpi__label", esc(label)));
      card.appendChild(h("div", "rp-kpi__value", esc(value)));
      card.appendChild(h("span", "rp-kpi__hint", esc(hint)));
      return card;
    };
    kpis.appendChild(kpi("Partite", String(s.games || 0), `${s.wins || 0}V · ${s.draws || 0}P · ${s.losses || 0}S`, true));
    kpis.appendChild(kpi("Media realizzata", num(s.avg_for), "punti a partita"));
    kpis.appendChild(kpi("Media subita", num(s.avg_against), "punti a partita"));
    kpis.appendChild(kpi("Differenza media", `${(s.avg_diff || 0) > 0 ? "+" : ""}${num(s.avg_diff)}`, "per partita"));
    kpis.appendChild(kpi("Serie attuale", streakLabel(s.current_streak), `record ${s.longest_win_streak || 0}V / ${s.longest_loss_streak || 0}S`));
    kpis.appendChild(kpi("Convocazioni", String(R.stats.convocations?.total || 0), `media ${num(R.stats.convocations?.average_per_match)} a gara`));
    wrap.appendChild(kpis);

    if (!s.games) {
      wrap.appendChild(
        (() => {
          const boxEl = h("div");
          boxEl.innerHTML = emptyBox(
            "📝",
            "Nessun referto definitivo",
            "Compila e salva un referto come definitivo per iniziare a vedere statistiche, andamenti e record.",
            "Vai alle partite",
            "data-rp-go-matches"
          );
          return boxEl;
        })()
      );
      box.appendChild(wrap);
      return;
    }

    const grid = h("div", "rp-grid rp-grid--2");

    const trendCard = h("div", "rp-card");
    const trendHead = h("div", "rp-card__head");
    trendHead.appendChild(h("div", null, '<div class="rp-card__title">Andamento punti</div><div class="rp-card__sub">Punti fatti e subiti nelle gare con referto</div>'));
    trendHead.appendChild(h("span", "rp-badge rp-badge--orange", plural(R.stats.trend.length, "gara", "gare")));
    trendCard.appendChild(trendHead);
    const trendRows = R.stats.trend.slice(-12);
    trendCard.appendChild(lineChart(trendRows, { label: "Andamento punti CarpeDiem" }));
    const trendLegend = h("div");
    trendLegend.innerHTML = legend();
    trendCard.appendChild(trendLegend);
    grid.appendChild(trendCard);

    const quarterCard = h("div", "rp-card");
    quarterCard.appendChild(h("div", "rp-card__head", '<div><div class="rp-card__title">Punti per quarto</div><div class="rp-card__sub">Totale stagione e media a gara</div></div>'));
    const qOurs = s.quarters?.ours || [0, 0, 0, 0];
    const qOpp = s.quarters?.opp || [0, 0, 0, 0];
    quarterCard.appendChild(quarterBars(qOurs, qOpp));
    const qLegend = h("div");
    qLegend.innerHTML = legend();
    quarterCard.appendChild(qLegend);
    const qAvg = h("div", "rp-hint");
    qAvg.style.marginTop = "10px";
    qAvg.textContent = `Media per quarto: ${(s.quarter_avg?.ours || []).map((v) => num(v)).join(" · ")}`;
    quarterCard.appendChild(qAvg);
    grid.appendChild(quarterCard);
    wrap.appendChild(grid);

    const scorers = h("div", "rp-card rp-card--flush");
    const scorersHead = h("div", "rp-card__head");
    scorersHead.style.padding = "18px 18px 0";
    scorersHead.appendChild(h("div", null, '<div class="rp-card__title">Migliori realizzatori</div><div class="rp-card__sub">Ordina per punti totali</div>'));
    scorers.appendChild(scorersHead);
    const scTable = h("div", "rp-table-wrap");
    scTable.style.border = "none";
    scTable.innerHTML = `<table class="rp-table"><thead><tr>
      <th></th><th>Giocatore</th><th class="num">Gare</th><th class="num">Punti</th><th class="num">Media</th><th class="num">Max</th><th>Quarti</th>
    </tr></thead><tbody>${(R.stats.top_scorers || [])
      .map(
        (player, index) => `<tr class="is-clickable" data-rp-player="${player.player_id}">
          <td class="rp-rank">${index + 1}</td>
          <td><div class="rp-namecell"><span class="rp-ava">${esc(initialsOf(player.name))}</span>
            <div><div class="rp-player-name">${esc(player.name)}</div><div class="rp-player-sub">${esc(player.role2_type || (player.role ? `Ruolo ${player.role}` : ""))}${player.jersey_number ? ` · #${player.jersey_number}` : ""}</div></div>
          </div></td>
          <td class="num">${player.games}</td>
          <td class="num strong">${player.points}</td>
          <td class="num">${num(player.avg)}</td>
          <td class="num">${player.max}</td>
          <td>${miniQuarters(player.q || [0, 0, 0, 0])}</td>
        </tr>`
      )
      .join("") || '<tr><td colspan="7" class="rp-hint">Nessun dato disponibile.</td></tr>'}</tbody></table>`;
    scorers.appendChild(scTable);
    wrap.appendChild(scorers);

    const grid2 = h("div", "rp-grid rp-grid--2");

    const recent = h("div", "rp-card");
    recent.appendChild(h("div", "rp-card__head", '<div><div class="rp-card__title">Ultime gare</div><div class="rp-card__sub">Risultati con referto definitivo</div></div>'));
    const recentList = h("div", "rp-stack");
    recentList.style.gap = "8px";
    (R.stats.matches || [])
      .slice(-5)
      .reverse()
      .forEach((match) => {
        const row = h("div", "rp-row rp-row--between");
        row.style.padding = "9px 11px";
        row.style.border = "1px solid var(--rp-line)";
        row.style.borderRadius = "10px";
        row.style.cursor = "pointer";
        row.onclick = () => openEditor(match.id);
        row.innerHTML = `<div style="min-width:0"><div class="rp-player-name">${match.home ? "vs" : "@"} ${esc(match.opponent?.name || "")}</div>
          <div class="rp-player-sub">${esc(shortDate(match.date))} · ${esc(match.federation)}</div></div>
          <div class="rp-row" style="gap:8px">${resultBadge(match.result)}<strong>${match.our_score}-${match.opp_score}</strong></div>`;
        recentList.appendChild(row);
      });
    if (!(R.stats.matches || []).length) recentList.appendChild(h("p", "rp-hint", "Nessuna gara."));
    recent.appendChild(recentList);
    grid2.appendChild(recent);

    const splitCard = h("div", "rp-card");
    splitCard.appendChild(h("div", "rp-card__head", '<div><div class="rp-card__title">Casa, trasferta e campionati</div><div class="rp-card__sub">Bilancio e medie punti</div></div>'));
    const splitGrid = h("div", "rp-grid rp-grid--3");
    const splitBox = (title, row) => {
      const card = h("div", "rp-kpi");
      card.appendChild(h("span", "rp-kpi__label", esc(title)));
      card.appendChild(h("div", "rp-kpi__value", `${row.wins || 0}-${row.losses || 0}${row.draws ? `-${row.draws}` : ""}`));
      card.appendChild(h("span", "rp-kpi__hint", `${row.games || 0} gare · ${num((row.points_for || 0) / (row.games || 1))} fatti · ${num((row.points_against || 0) / (row.games || 1))} subiti`));
      return card;
    };
    splitGrid.appendChild(splitBox("In casa", s.home || {}));
    splitGrid.appendChild(splitBox("In trasferta", s.away || {}));
    (s.federation_split || []).forEach((fed) => splitGrid.appendChild(splitBox(fed.code || "—", fed)));
    splitCard.appendChild(splitGrid);
    grid2.appendChild(splitCard);
    wrap.appendChild(grid2);

    box.appendChild(wrap);
  }

  function streakLabel(streak) {
    if (!streak || !streak.count) return "—";
    const prefix = streak.type === "W" ? "V" : streak.type === "L" ? "S" : "P";
    return `${streak.count}${prefix}`;
  }

  async function syncPublic(button) {
    if (!confirm("Importare dal calendario pubblico gare e convocazioni? Le gare già presenti non vengono duplicate.")) return;
    const original = button.textContent;
    button.disabled = true;
    button.textContent = "Sincronizzazione…";
    try {
      const result = await rApi("/api/admin/sync-public", { method: "POST" });
      toast(`Sincronizzate ${result.convocations ?? 0} convocazioni${result.warnings?.length ? ` · ${result.warnings.length} avvisi` : ""}`);
      R.loaded = false;
      await loadBoard(true);
      await loadStats(true);
      rpRender();
    } catch (error) {
      toast(error.message || "Sincronizzazione non riuscita");
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  }

  /* ------------------------------- Matches ------------------------------- */

  function renderMatches(box) {
    const wrap = h("div", "rp-stack");
    const head = h("div", "rp-row rp-row--between");
    head.appendChild(h("div", null, '<div class="rp-card__title">Partite & referti</div><div class="rp-card__sub">Apri una gara per compilare il referto in stile Excel</div>'));
    const sync = h("button", "rp-btn rp-btn--soft", "⟳ Sincronizza calendario");
    sync.onclick = () => syncPublic(sync);
    head.appendChild(sync);
    wrap.appendChild(head);

    const bar = h("div", "rp-filterbar");
    const search = h("div", "rp-search");
    const input = h("input");
    input.type = "search";
    input.placeholder = "Cerca avversario o data…";
    input.value = R.search;
    input.oninput = () => {
      R.search = input.value;
      renderMatchList(host);
    };
    search.appendChild(input);
    bar.appendChild(search);

    [["all", "Tutte"], ["todo", "Da compilare"], ["draft", "Bozze"], ["final", "Definitive"]].forEach(([key, label]) => {
      const button = h("button", "rp-tab" + (R.matchFilter === key ? " is-active" : ""), label);
      button.onclick = () => {
        R.matchFilter = key;
        bar.querySelectorAll(".rp-tab").forEach((tab) => tab.classList.toggle("is-active", tab === button));
        renderMatchList(host);
      };
      bar.appendChild(button);
    });
    wrap.appendChild(bar);

    const host = h("div");
    wrap.appendChild(host);
    renderMatchList(host);
    box.appendChild(wrap);
  }

  function renderMatchList(host) {
    const matches = (R.board?.matches || []).filter((match) => {
      if (R.matchFilter === "todo" && match.report_status) return false;
      if (R.matchFilter === "draft" && match.report_status !== "draft") return false;
      if (R.matchFilter === "final" && match.report_status !== "final") return false;
      if (R.search) {
        const text = `${match.opponent?.name || ""} ${match.date || ""} ${match.federation || ""}`.toLowerCase();
        if (!text.includes(R.search.toLowerCase())) return false;
      }
      return true;
    });

    host.innerHTML = "";
    if (!matches.length) {
      host.innerHTML = emptyBox("🔎", "Nessuna gara trovata", "Modifica i filtri oppure sincronizza il calendario pubblico.");
      return;
    }

    const list = h("div", "rp-matches");
    matches.forEach((match) => {
      const status = match.report_status;
      const badge = status === "final"
        ? '<span class="rp-badge rp-badge--final">Definitivo</span>'
        : status === "draft"
        ? '<span class="rp-badge rp-badge--draft">Bozza</span>'
        : '<span class="rp-badge rp-badge--muted">Da compilare</span>';

      const card = h("div", "rp-match" + (status ? "" : " is-missing"));
      card.onclick = () => openEditor(match.id);

      const top = h("div", "rp-match__top");
      top.innerHTML = `<div class="rp-match__date">${esc(shortDate(match.date))}${match.time ? ` · ${esc(String(match.time).slice(0, 5))}` : ""}</div>
        <div class="rp-row" style="gap:6px">${fedPill(match.federation)}${badge}</div>`;
      card.appendChild(top);

      const main = h("div", "rp-match__main");
      const logo = h("div", "rp-match__logo", esc(initialsOf(match.opponent?.name || "?")));
      main.appendChild(logo);
      const info = h("div");
      info.style.minWidth = "0";
      info.innerHTML = `<div class="rp-match__opp">${match.home ? "vs" : "@"} ${esc(match.opponent?.name || "")}</div>
        <div class="rp-match__meta">${esc(match.competition || "")}${match.matchday ? ` · Giornata ${match.matchday}` : ""}${match.venue ? ` · ${esc(match.venue.name)}` : ""}</div>`;
      main.appendChild(info);

      if (match.score_source !== "none") {
        const score = h("div", "rp-match__score");
        score.innerHTML = `<b>${match.our_score}-${match.opp_score}</b><small>${esc(match.score_source === "report" ? "referto" : "calendario")}</small>`;
        main.appendChild(score);
      }
      card.appendChild(main);

      const foot = h("div", "rp-match__foot");
      const left = h("div", "rp-row");
      left.style.gap = "6px";
      if (match.has_convocations) left.innerHTML += `<span class="rp-badge">📋 ${match.convocations_count}</span>`;
      if (match.top_scorer) left.innerHTML += `<span class="rp-badge rp-badge--orange">★ ${esc(match.top_scorer.name)} ${match.top_scorer.total}</span>`;
      foot.appendChild(left);

      const action = h("span", "rp-badge rp-badge--orange", status ? "Apri referto →" : "Compila →");
      foot.appendChild(action);
      card.appendChild(foot);

      if (match.score_mismatch) {
        const warn = h("div", "rp-match__warn");
        warn.innerHTML = `⚠️ Punteggio calendario diverso dal referto (${match.calendar_score.home}-${match.calendar_score.away})`;
        card.appendChild(warn);
      }
      list.appendChild(card);
    });
    host.appendChild(list);
  }

  /* ------------------------------- Players ------------------------------- */

  function renderPlayers(box) {
    const wrap = h("div", "rp-stack");

    if (R.playerId) {
      renderPlayerDetail(wrap, R.playerId);
      box.appendChild(wrap);
      return;
    }

    const head = h("div", "rp-row rp-row--between");
    head.appendChild(h("div", null, '<div class="rp-card__title">Giocatori</div><div class="rp-card__sub">Punti, medie, record e avversari affrontati</div>'));
    wrap.appendChild(head);

    const bar = h("div", "rp-filterbar");
    const search = h("div", "rp-search");
    const input = h("input");
    input.type = "search";
    input.placeholder = "Cerca giocatore…";
    input.value = R.playerSearch;
    input.oninput = () => {
      R.playerSearch = input.value;
      renderPlayerTable(host);
    };
    search.appendChild(input);
    bar.appendChild(search);

    const sort = h("select");
    [["points", "Punti totali"], ["avg", "Media punti"], ["max", "Record in una gara"], ["games", "Gare giocate"], ["convocations", "Convocazioni"]].forEach(([value, label]) => {
      const option = h("option", null, label);
      option.value = value;
      option.selected = R.playerSort === value;
      sort.appendChild(option);
    });
    sort.onchange = () => {
      R.playerSort = sort.value;
      renderPlayerTable(host);
    };
    bar.appendChild(sort);

    const sortLabel = h("span", "rp-hint", "Ordina per");
    bar.insertBefore(sortLabel, sort);
    wrap.appendChild(bar);

    const host = h("div");
    wrap.appendChild(host);

    if (!R.stats) {
      host.innerHTML = '<div class="rp-skeleton"><div class="rp-skel" style="height:220px"></div></div>';
      loadStats().then(() => rpRender());
    } else {
      renderPlayerTable(host);
    }
    box.appendChild(wrap);
  }

  function renderPlayerTable(host) {
    const rows = (R.stats?.players || [])
      .filter((player) => {
        if (!R.playerSearch) return true;
        return `${player.name} ${player.jersey_number || ""}`.toLowerCase().includes(R.playerSearch.toLowerCase());
      })
      .sort((a, b) => {
        const key = R.playerSort;
        return (b[key] || 0) - (a[key] || 0);
      });

    if (!rows.length) {
      host.innerHTML = emptyBox("👤", "Nessun giocatore con referti", "Salva un referto definitivo per popolare le statistiche individuali.");
      return;
    }

    host.innerHTML = `<div class="rp-table-wrap"><table class="rp-table">
      <thead><tr>
        <th></th><th>Giocatore</th><th class="num">#</th><th class="num">Gare</th><th class="num">Conv.</th><th class="num">Pres.</th>
        <th class="num">Punti</th><th class="num">Media</th><th class="num">Max</th><th>Quarti</th><th>Record</th>
      </tr></thead>
      <tbody>${rows
        .map(
          (player, index) => `<tr class="is-clickable" data-rp-player="${player.player_id}">
            <td class="rp-rank">${index + 1}</td>
            <td><div class="rp-namecell"><span class="rp-ava">${esc(initialsOf(player.name))}</span>
              <div><div class="rp-player-name">${esc(player.name)}</div><div class="rp-player-sub">${esc(player.role2_type || (player.role ? `Ruolo ${player.role}` : ""))}</div></div>
            </div></td>
            <td class="num">${player.jersey_number != null ? player.jersey_number : "—"}</td>
            <td class="num">${player.games}</td>
            <td class="num">${player.convocations}</td>
            <td class="num">${player.participation != null ? `${Math.round(player.participation * 100)}%` : "—"}</td>
            <td class="num strong">${player.points}</td>
            <td class="num">${num(player.avg)}</td>
            <td class="num">${player.max}</td>
            <td>${miniQuarters(player.q || [0, 0, 0, 0])}</td>
            <td class="rp-player-sub">${player.max_game ? `${player.max_game.total} vs ${esc(player.max_game.opponent)}` : "—"}</td>
          </tr>`
        )
        .join("")}</tbody></table></div>
      <div class="rp-hint" style="margin-top:10px">Tocca un giocatore per il dettaglio completo: media, record, avversari e cronologia.</div>`;
  }

  function renderPlayerDetail(wrap, playerId) {
    const head = h("div", "rp-row");
    const back = h("button", "rp-btn rp-btn--ghost", "← Tutti i giocatori");
    back.onclick = () => {
      R.playerId = null;
      R.playerDetail = null;
      R.playerLoading = false;
      rpRender();
    };
    head.appendChild(back);
    wrap.appendChild(head);

    if (!R.playerDetail && !R.playerLoading) {
      R.playerLoading = true;
      rApi(`/api/admin/reports/players/${playerId}${seasonQuery()}`)
        .then((data) => {
          R.playerDetail = data;
        })
        .catch((error) => {
          R.error = error;
        })
        .finally(() => {
          R.playerLoading = false;
          rpRender();
        });
    }

    if (!R.playerDetail) {
      wrap.appendChild(h("div", "rp-skeleton", '<div class="rp-skel" style="height:120px"></div><div class="rp-skel" style="height:220px"></div>'));
      return;
    }

    const d = R.playerDetail;
    const p = d.player;
    const s = d.summary;

    const banner = h("div", "rp-card");
    banner.style.display = "flex";
    banner.style.alignItems = "center";
    banner.style.gap = "16px";
    banner.style.flexWrap = "wrap";
    const ava = h("span", "rp-ava rp-ava--lg", esc(initialsOf(`${p.first_name} ${p.last_name}`)));
    banner.appendChild(ava);
    const info = h("div");
    info.style.flex = "1 1 220px";
    info.innerHTML = `<div class="rp-eyebrow">${esc(p.role2_type || (p.role ? `Ruolo ${p.role}` : "Giocatore"))}${p.jersey_number != null ? ` · #${p.jersey_number}` : ""}</div>
      <h2 style="font-size:1.5rem;margin:4px 0">${esc(p.name)}</h2>
      <div class="rp-hint">Stagione ${esc(d.season)} · ${plural(s.games, "gara", "gare")} con referto · ${plural(s.convocations, "convocazione", "convocazioni")}</div>`;
    banner.appendChild(info);
    const pts = h("div");
    pts.style.textAlign = "right";
    pts.innerHTML = `<div class="rp-kpi__label">Punti totali</div><div style="font-size:2.2rem;font-weight:900;color:var(--rp-orange-2);line-height:1">${s.points}</div>
      <div class="rp-hint">media ${num(s.avg)} · record ${s.max}</div>`;
    banner.appendChild(pts);
    wrap.appendChild(banner);

    const kpis = h("div", "rp-grid rp-grid--kpi");
    const kpi = (label, value, hint) => {
      const card = h("div", "rp-kpi");
      card.appendChild(h("span", "rp-kpi__label", esc(label)));
      card.appendChild(h("div", "rp-kpi__value", esc(value)));
      card.appendChild(h("span", "rp-kpi__hint", esc(hint || "")));
      return card;
    };
    kpis.appendChild(kpi("Gare giocate", String(s.games), `${s.wins}V · ${s.draws}P · ${s.losses}S`));
    kpis.appendChild(kpi("Partecipazione", s.participation != null ? `${Math.round(s.participation * 100)}%` : "—", plural(s.convocations, "convocazione", "convocazioni")));
    kpis.appendChild(kpi("Media punti", num(s.avg), "per gara giocata"));
    kpis.appendChild(kpi("Record", String(s.max), s.max_game ? `vs ${s.max_game.opponent}` : "—"));
    wrap.appendChild(kpis);

    const grid = h("div", "rp-grid rp-grid--2");

    const qCard = h("div", "rp-card");
    qCard.appendChild(h("div", "rp-card__head", '<div><div class="rp-card__title">Punti per quarto</div><div class="rp-card__sub">Totale e media personale</div></div>'));
    qCard.appendChild(quarterBars(s.quarters || [0, 0, 0, 0], [0, 0, 0, 0]));
    const qNote = h("div", "rp-hint");
    qNote.style.marginTop = "8px";
    qNote.textContent = `Media: ${(s.quarter_avg || []).map((value) => num(value)).join(" · ")}`;
    qCard.appendChild(qNote);
    grid.appendChild(qCard);

    const trendCard = h("div", "rp-card");
    trendCard.appendChild(h("div", "rp-card__head", '<div><div class="rp-card__title">Andamento personale</div><div class="rp-card__sub">Punti nelle ultime gare</div></div>'));
    const rows = (d.trend || []).slice(-12).map((item) => ({
      date: item.date,
      opponent: item.opponent,
      our_score: item.total,
      opp_score: 0,
    }));
    if (rows.length) trendCard.appendChild(lineChart(rows, { label: "Andamento punti giocatore" }));
    else trendCard.appendChild(h("p", "rp-hint", "Nessuna gara disponibile."));
    grid.appendChild(trendCard);
    wrap.appendChild(grid);

    const oppCard = h("div", "rp-card");
    oppCard.appendChild(h("div", "rp-card__head", '<div><div class="rp-card__title">Contro ogni avversario</div><div class="rp-card__sub">Punti totali, media e record personale</div></div>'));
    oppCard.insertAdjacentHTML(
      "beforeend",
      `<div class="rp-table-wrap" style="border:none"><table class="rp-table">
        <thead><tr><th>Avversario</th><th class="num">Gare</th><th class="num">Punti</th><th class="num">Media</th><th class="num">Max</th><th class="num">V-S</th></tr></thead>
        <tbody>${(d.opponents || [])
          .map(
            (row) => `<tr><td class="strong">${esc(row.opponent)}</td><td class="num">${row.games}</td><td class="num">${row.points}</td>
              <td class="num">${num(row.avg)}</td><td class="num strong">${row.max}</td><td class="num">${row.wins}-${row.losses}</td></tr>`
          )
          .join("") || '<tr><td colspan="6" class="rp-hint">Nessun dato.</td></tr>'}</tbody></table></div>`
    );
    wrap.appendChild(oppCard);

    const logCard = h("div", "rp-card");
    logCard.appendChild(h("div", "rp-card__head", '<div><div class="rp-card__title">Cronologia gare</div><div class="rp-card__sub">Dettaglio quarto per quarto</div></div>'));
    const games = [...(d.games || [])].reverse();
    logCard.insertAdjacentHTML(
      "beforeend",
      `<div class="rp-table-wrap" style="border:none"><table class="rp-table">
        <thead><tr><th>Data</th><th>Avversario</th><th></th><th class="num">1Q</th><th class="num">2Q</th><th class="num">3Q</th><th class="num">4Q</th><th class="num">Tot</th><th class="num">Ris.</th></tr></thead>
        <tbody>${games
          .map(
            (game) => `<tr>
              <td>${esc(shortDate(game.date))}</td>
              <td>${game.home ? "vs" : "@"} ${esc(game.opponent)}</td>
              <td>${resultBadge(game.result)}</td>
              <td class="num">${game.quarters[0]}</td><td class="num">${game.quarters[1]}</td>
              <td class="num">${game.quarters[2]}</td><td class="num">${game.quarters[3]}</td>
              <td class="num strong">${game.total}</td>
              <td class="num">${game.our_score}-${game.opp_score}</td>
            </tr>`
          )
          .join("") || '<tr><td colspan="9" class="rp-hint">Nessuna gara.</td></tr>'}</tbody></table></div>`
    );
    wrap.appendChild(logCard);
  }

  /* ------------------------------ Opponents ------------------------------ */

  function renderOpponents(box) {
    const wrap = h("div", "rp-stack");
    const head = h("div", "rp-row rp-row--between");
    head.appendChild(h("div", null, '<div class="rp-card__title">Avversari</div><div class="rp-card__sub">Bilancio, medie e miglior realizzatore contro ogni squadra</div>'));
    wrap.appendChild(head);

    if (!R.stats) {
      wrap.innerHTML += '<div class="rp-skeleton"><div class="rp-skel" style="height:240px"></div></div>';
      box.appendChild(wrap);
      loadStats().then(() => rpRender());
      return;
    }

    const rows = R.stats.opponents || [];
    if (!rows.length) {
      wrap.appendChild((() => {
        const node = h("div");
        node.innerHTML = emptyBox("🤝", "Nessun avversario", "Serve almeno un referto definitivo per costruire lo storico avversari.");
        return node;
      })());
      box.appendChild(wrap);
      return;
    }

    const cards = h("div", "rp-grid rp-grid--3");
    rows.forEach((team) => {
      const card = h("div", "rp-card");
      card.appendChild(
        h(
          "div",
          "rp-card__head",
          `<div><div class="rp-card__title">${esc(team.name)}</div>
            <div class="rp-card__sub">${plural(team.games, "gara", "gare")} · ${team.wins}V ${team.draws}P ${team.losses}S</div></div>
            ${resultBadge(team.last_result?.result)}`
        )
      );
      const stats = h("div", "rp-grid rp-grid--kpi");
      stats.style.gridTemplateColumns = "repeat(3, 1fr)";
      const stat = (label, value) => {
        const node = h("div", "rp-kpi");
        node.style.minHeight = "78px";
        node.appendChild(h("span", "rp-kpi__label", label));
        node.appendChild(h("div", "rp-kpi__value", value));
        return node;
      };
      stats.appendChild(stat("Media fatti", num(team.avg_for)));
      stats.appendChild(stat("Media subiti", num(team.avg_against)));
      stats.appendChild(stat("Differenza", `${team.diff > 0 ? "+" : ""}${team.diff}`));
      card.appendChild(stats);

      const foot = h("div", "rp-hint");
      foot.style.marginTop = "12px";
      foot.innerHTML = `<div>Miglior gara: <strong>${team.best_for ? team.best_for.score : "—"}</strong> punti${team.best_for ? ` (${esc(shortDate(team.best_for.date))})` : ""}</div>
        <div>Peggior difesa: <strong>${team.worst_against ? team.worst_against.score : "—"}</strong> subiti${team.worst_against ? ` (${esc(shortDate(team.worst_against.date))})` : ""}</div>
        <div>Top scorer: <strong>${team.top_scorer ? `${esc(team.top_scorer.name)} (${team.top_scorer.points})` : "—"}</strong></div>`;
      card.appendChild(foot);
      cards.appendChild(card);
    });
    wrap.appendChild(cards);
    box.appendChild(wrap);
  }

  /* ------------------------------- Editor -------------------------------- */

  let rpSeq = 1;

  function mkEditor(payload) {
    const lines = (payload.report.lines || []).map((line, index) => ({
      ...line,
      _key: `l${rpSeq++}`,
      q1: Number(line.q1) || 0,
      q2: Number(line.q2) || 0,
      q3: Number(line.q3) || 0,
      q4: Number(line.q4) || 0,
      sort_order: index,
    }));
    return {
      matchId: payload.match.id,
      payload,
      lines,
      side: lines.some((line) => line.team_side === "ours") ? "ours" : "opponent",
      status: payload.report.status || "draft",
      notes: payload.report.notes || "",
      syncScore: true,
      advanced: false,
      dirty: false,
      saving: false,
    };
  }

  async function openEditor(matchId) {
    R.playerId = null;
    R.playerDetail = null;
    const box = document.getElementById("reportsView");
    box.innerHTML = `<div class="rp"><div class="rp-skeleton">
      <div class="rp-skel" style="height:90px"></div>
      <div class="rp-skel" style="height:300px"></div>
    </div></div>`;
    try {
      const payload = await rApi(`/api/admin/reports/${matchId}`);
      R.editor = mkEditor(payload);
      rpRender();
    } catch (error) {
      toast(error.message || "Impossibile aprire il referto");
      R.error = error;
      R.editor = null;
      rpRender();
    }
  }

  function closeEditor(force = false) {
    if (!R.editor) return;
    if (!force && R.editor.dirty && !confirm("Ci sono modifiche non salvate. Uscire comunque?")) return;
    R.editor = null;
    R.section = "matches";
    rpRender();
  }

  function editorNode() {
    const ed = R.editor;
    const match = ed.payload.match;
    const oursTeam = match.home_team && match.home_team.is_ours ? match.home_team : match.away_team;
    const wrap = h("div", "rp-editor");

    const oursName = oursTeam?.name || "CarpeDiem";
    const oppName = match.opponent?.name || "Avversario";

    const sb = h("div", "rp-scoreboard");
    const back = h("button", "rp-scoreboard__back", "←");
    back.title = "Torna alle partite";
    back.onclick = () => closeEditor();
    sb.appendChild(back);

    const teams = h("div", "rp-scoreboard__teams");
    teams.innerHTML = `<div class="rp-sb-team">
        <div class="rp-sb-team__name">${esc(oursName)}</div>
        <div class="rp-sb-team__sub">${match.home ? "In casa" : "Trasferta"} · ${esc(match.federation || "")}</div>
      </div>
      <div class="rp-sb-score"><span class="is-ours" id="rpScoreUs">0</span><em>–</em><span id="rpScoreThem">0</span></div>
      <div class="rp-sb-team">
        <div class="rp-sb-team__name">${esc(oppName)}</div>
        <div class="rp-sb-team__sub">${esc(shortDate(match.date))}</div>
      </div>`;
    sb.appendChild(teams);

    const actions = h("div", "rp-scoreboard__actions");
    const statusBadge = h("span", `rp-badge ${ed.status === "final" ? "rp-badge--final" : "rp-badge--draft"}`, ed.status === "final" ? "Definitivo" : "Bozza");
    statusBadge.id = "rpStatusBadge";
    actions.appendChild(statusBadge);
    const dirtyTag = h("span", "rp-badge rp-badge--warn", "Modifiche non salvate");
    dirtyTag.id = "rpDirtyTag";
    dirtyTag.hidden = !ed.dirty;
    actions.appendChild(dirtyTag);

    const draftButton = h("button", "rp-btn rp-btn--ghost", "Salva bozza");
    draftButton.onclick = () => saveEditor("draft");
    actions.appendChild(draftButton);

    const finalButton = h("button", "rp-btn rp-btn--primary", "Salva definitivo");
    finalButton.onclick = () => saveEditor("final");
    actions.appendChild(finalButton);
    sb.appendChild(actions);
    wrap.appendChild(sb);

    (ed.payload.warnings || []).forEach((warning) => {
      const warn = h("div", "rp-warnbox", `⚠️ <span>${esc(warning)}</span>`);
      wrap.appendChild(warn);
    });
    if (match.score_mismatch) {
      const warn = h("div", "rp-warnbox", `⚠️ <span>Il calendario indica <strong>${match.calendar_score.home}-${match.calendar_score.away}</strong> mentre il referto calcola <strong>${match.home ? `${match.our_score}-${match.opp_score}` : `${match.opp_score}-${match.our_score}`}</strong>. Salvando come definitivo con l'opzione attiva il punteggio verrà allineato.</span>`);
      wrap.appendChild(warn);
    }

    const bar = h("div", "rp-editor__bar");
    const sideTabs = h("div", "rp-side-tabs");
    [["ours", oursName], ["opponent", oppName]].forEach(([key, label]) => {
      const count = ed.lines.filter((line) => line.team_side === key).length;
      const button = h("button", ed.side === key ? "is-active" : "", `${esc(label)}<small>${count}</small>`);
      button.onclick = () => {
        ed.side = key;
        rpRenderLines();
        sideTabs.querySelectorAll("button").forEach((node) => node.classList.toggle("is-active", node === button));
      };
      sideTabs.appendChild(button);
    });
    bar.appendChild(sideTabs);

    const barActions = h("div", "rp-row");
    const advButton = h("button", "rp-btn rp-btn--sm" + (ed.advanced ? " rp-btn--soft" : ""), "Statistiche avanzate");
    advButton.onclick = () => {
      ed.advanced = !ed.advanced;
      advButton.classList.toggle("rp-btn--soft", ed.advanced);
      rpRenderLines();
    };
    barActions.appendChild(advButton);

    const importButton = h("button", "rp-btn rp-btn--sm rp-btn--soft", "⬆ Importa Excel");
    importButton.onclick = () => openImportModal();
    barActions.appendChild(importButton);

    const addButton = h("button", "rp-btn rp-btn--sm", "+ Aggiungi riga");
    addButton.onclick = () => {
      const line = {
        _key: `l${rpSeq++}`,
        team_side: ed.side,
        player_id: null,
        player_name: "",
        jersey_number: null,
        played: true,
        q1: 0,
        q2: 0,
        q3: 0,
        q4: 0,
        sort_order: ed.lines.length,
      };
      ed.lines.push(line);
      ed.dirty = true;
      rpRenderLines();
      const row = document.querySelector(`[data-key="${line._key}"]`);
      if (row) {
        row.scrollIntoView({ block: "nearest", behavior: "smooth" });
        const field = row.querySelector(ed.side === "ours" ? ".rp-cell" : "[data-line-field='player_name']");
        if (field) field.focus();
      }
    };
    barActions.appendChild(addButton);
    bar.appendChild(barActions);
    wrap.appendChild(bar);

    const host = h("div");
    host.id = "rpLinesHost";
    wrap.appendChild(host);

    if (ed.side === "ours") {
      const hint = h("div", "rp-hint");
      hint.id = "rpOursHint";
      hint.style.marginTop = "-4px";
      hint.textContent = "Seleziona i giocatori dalla rosa: i nomi non abbinati restano nel referto ma non entrano nelle statistiche individuali.";
      wrap.appendChild(hint);
    }

    const meta = h("div", "rp-card");
    meta.appendChild(h("div", "rp-card__title", "Note e opzioni"));
    meta.style.marginTop = "4px";
    const notes = h("textarea");
    notes.placeholder = "Note sulla gara (arbitri, infortuni, commenti…)";
    notes.value = ed.notes || "";
    notes.style.marginTop = "10px";
    notes.oninput = () => {
      ed.notes = notes.value;
      ed.dirty = true;
      rpMarkDirty();
    };
    meta.appendChild(notes);

    const options = h("div", "rp-row");
    options.style.marginTop = "10px";
    const syncLabel = h("label", "rp-hint");
    syncLabel.style.display = "inline-flex";
    syncLabel.style.alignItems = "center";
    syncLabel.style.gap = "7px";
    const syncCheck = h("input");
    syncCheck.type = "checkbox";
    syncCheck.checked = ed.syncScore;
    syncCheck.onchange = () => {
      ed.syncScore = syncCheck.checked;
      ed.dirty = true;
      rpMarkDirty();
    };
    syncLabel.appendChild(syncCheck);
    syncLabel.appendChild(document.createTextNode("Salvando come definitivo aggiorna il punteggio nel calendario"));
    options.appendChild(syncLabel);
    options.appendChild(h("div", "rp-spacer"));

    if (ed.payload.report.id) {
      const deleteButton = h("button", "rp-btn rp-btn--sm rp-btn--danger", "Elimina referto");
      deleteButton.onclick = () => deleteReport();
      options.appendChild(deleteButton);
    }
    meta.appendChild(options);
    wrap.appendChild(meta);

    setTimeout(() => {
      rpRenderLines();
      rpRefreshTotals();
    }, 0);
    return wrap;
  }

  function markDirty() {
    if (!R.editor) return;
    R.editor.dirty = true;
    rpMarkDirty();
  }

  function rpMarkDirty() {
    const tag = document.getElementById("rpDirtyTag");
    if (tag) tag.hidden = !R.editor?.dirty;
  }

  function playerMap() {
    const map = new Map();
    (R.editor?.payload.eligible_players || []).forEach((player) => map.set(player.id, player));
    (R.editor?.payload.convocations || []).forEach((item) => {
      if (item.player) map.set(item.player.id, item.player);
    });
    (R.editor?.lines || []).forEach((line) => {
      if (line.player) map.set(line.player.id, line.player);
    });
    return map;
  }

  function oursNameCell(line, players) {
    const options = [`<option value="">${line.player_id ? "— seleziona —" : esc(line.player_name || "— seleziona giocatore —")}</option>`];
    [...players.values()]
      .sort((a, b) => String(a.last_name || "").localeCompare(String(b.last_name || ""), "it"))
      .forEach((player) => {
        const label = `${player.name}${player.jersey_number != null ? ` (#${player.jersey_number})` : ""}${player.role2_type ? ` · ${player.role2_type}` : ""}`;
        options.push(`<option value="${player.id}" ${line.player_id === player.id ? "selected" : ""}>${esc(label)}</option>`);
      });
    return `<div class="rp-row" style="gap:4px;flex-wrap:nowrap">
      <select class="rp-cell" data-line-player style="flex:1">${options.join("")}</select>
      <button class="rp-rowbtn" data-line-custom title="Inserisci un nome libero">✎</button>
    </div>`;
  }

  function lineRow(line, players) {
    const isOurs = line.team_side === "ours";
    const nameCell = isOurs
      ? oursNameCell(line, players)
      : `<input class="rp-cell" data-line-field="player_name" list="rpOppNames" value="${esc(line.player_name || "")}" placeholder="Nome giocatore avversario" style="text-align:left" />`;
    const advanced = R.editor.advanced
      ? ["fouls", "rebounds", "assists", "steals", "turnovers", "blocks", "minutes"]
          .map(
            (field) =>
              `<td><input class="rp-cell" type="number" min="0" data-line-field="${field}" value="${line[field] != null ? line[field] : ""}" /></td>`
          )
          .join("")
      : "";
    const qCells = [1, 2, 3, 4]
      .map(
        (q) =>
          `<td><input class="rp-cell ${line[`q${q}`] ? "is-filled" : ""}" type="number" min="0" inputmode="numeric" data-line-q="${q}" value="${line[`q${q}`] || 0}" /></td>`
      )
      .join("");
    return `<tr data-key="${line._key}" class="${line.played ? "" : "is-out"}">
      <td style="text-align:center"><input class="rp-played" type="checkbox" data-line-played ${line.played ? "checked" : ""} title="Ha giocato" /></td>
      <td><input class="rp-cell" type="number" min="0" data-line-field="jersey_number" value="${line.jersey_number != null ? line.jersey_number : ""}" placeholder="—" /></td>
      <td class="rp-col-name">${nameCell}</td>
      ${qCells}
      <td class="rp-total" data-line-total>${(line.q1 || 0) + (line.q2 || 0) + (line.q3 || 0) + (line.q4 || 0)}</td>
      ${advanced}
      <td style="text-align:center"><button class="rp-rowbtn" data-line-remove title="Rimuovi riga">✕</button></td>
    </tr>`;
  }

  function rpRenderLines() {
    const host = document.getElementById("rpLinesHost");
    if (!host || !R.editor) return;
    const ed = R.editor;
    const players = playerMap();
    const lines = ed.lines.filter((line) => line.team_side === ed.side);
    const advancedHead = ed.advanced
      ? ["Falli", "Rimbalzi", "Assist", "Recuperi", "Perse", "Stoppate", "Minuti"].map((label) => `<th>${label}</th>`).join("")
      : "";

    host.innerHTML = `<div class="rp-lines-wrap">
      <table class="rp-lines">
        <thead><tr>
          <th title="Ha giocato">✓</th><th class="rp-col-num">#</th><th class="rp-col-name">${ed.side === "ours" ? "Giocatore CarpeDiem" : "Giocatore avversario"}</th>
          <th>1Q</th><th>2Q</th><th>3Q</th><th>4Q</th><th>Tot</th>
          ${advancedHead}<th></th>
        </tr></thead>
        <tbody>${lines.map((line) => lineRow(line, players)).join("")}</tbody>
        <tfoot><tr>
          <td colspan="3">Totale ${ed.side === "ours" ? "CarpeDiem" : "avversari"}</td>
          <td data-side-total="q1"></td><td data-side-total="q2"></td><td data-side-total="q3"></td><td data-side-total="q4"></td>
          <td data-side-total="total"></td>
          ${ed.advanced ? `<td colspan="7"></td>` : ""}
          <td></td>
        </tr></tfoot>
      </table>
      ${lines.length ? "" : '<div class="rp-empty" style="border:none">➕ Nessuna riga: usa “Aggiungi riga” o importa il file Excel.</div>'}
    </div>
    <datalist id="rpOppNames">${(ed.payload.opponent_suggestions || [])
      .map((item) => `<option value="${esc(item.player_name)}">${item.games} gare · #${item.jersey_number ?? "—"}</option>`)
      .join("")}</datalist>`;

    const oursHint = document.getElementById("rpOursHint");
    if (oursHint) oursHint.hidden = ed.side !== "ours";

    host.querySelectorAll("tr[data-key]").forEach((row) => {
      const line = ed.lines.find((item) => item._key === row.dataset.key);
      if (!line) return;

      const played = row.querySelector("[data-line-played]");
      if (played) {
        played.onchange = () => {
          line.played = played.checked;
          row.classList.toggle("is-out", !line.played);
          markDirty();
        };
      }

      row.querySelectorAll("[data-line-q]").forEach((input) => {
        input.oninput = () => {
          const q = input.dataset.lineQ;
          line[`q${q}`] = clampInt(input.value);
          input.classList.toggle("is-filled", !!line[`q${q}`]);
          rpRefreshTotals();
          markDirty();
        };
        input.onblur = () => {
          input.value = String(line[`q${input.dataset.lineQ}`] || 0);
        };
        input.onkeydown = (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            const inputs = [...host.querySelectorAll("tr[data-key] [data-line-q]")];
            const next = inputs[inputs.indexOf(input) + 4];
            if (next) next.focus();
          }
        };
      });

      row.querySelectorAll("[data-line-field]").forEach((input) => {
        input.oninput = () => {
          const field = input.dataset.lineField;
          if (field === "player_name") line.player_name = input.value;
          else if (field === "jersey_number") line.jersey_number = input.value === "" ? null : clampInt(input.value);
          else line[field] = input.value === "" ? null : clampInt(input.value);
          markDirty();
        };
      });

      const select = row.querySelector("[data-line-player]");
      if (select) {
        select.onchange = () => {
          const playersMap = playerMap();
          if (!select.value) {
            line.player_id = null;
            line.player_name = "";
          } else {
            const playerId = Number(select.value);
            if (ed.lines.some((other) => other !== line && other.player_id === playerId)) {
              toast("Giocatore già presente nel referto");
              select.value = line.player_id ? String(line.player_id) : "";
              return;
            }
            const player = playersMap.get(playerId);
            if (!player) return;
            line.player_id = player.id;
            line.player_name = player.name;
            if (line.jersey_number == null && player.jersey_number != null) line.jersey_number = player.jersey_number;
          }
          markDirty();
          rpRenderLines();
        };
      }

      const custom = row.querySelector("[data-line-custom]");
      if (custom) {
        custom.onclick = () => {
          const name = prompt("Nome da riportare nel referto:", line.player_name || "");
          if (name === null) return;
          line.player_id = null;
          line.player_name = name.trim();
          markDirty();
          rpRenderLines();
        };
      }

      const remove = row.querySelector("[data-line-remove]");
      if (remove) {
        remove.onclick = () => {
          const index = ed.lines.indexOf(line);
          if (index >= 0) ed.lines.splice(index, 1);
          ed.lines.forEach((item, i) => (item.sort_order = i));
          markDirty();
          rpRenderLines();
          rpRefreshTotals();
        };
      }
    });

    rpRefreshTotals();
  }

  function sideTotals(side) {
    const totals = { q1: 0, q2: 0, q3: 0, q4: 0, total: 0 };
    (R.editor?.lines || [])
      .filter((line) => line.team_side === side)
      .forEach((line) => {
        totals.q1 += line.q1 || 0;
        totals.q2 += line.q2 || 0;
        totals.q3 += line.q3 || 0;
        totals.q4 += line.q4 || 0;
        totals.total += (line.q1 || 0) + (line.q2 || 0) + (line.q3 || 0) + (line.q4 || 0);
      });
    return totals;
  }

  function rpRefreshTotals() {
    if (!R.editor) return;
    const ed = R.editor;
    (ed.lines || []).forEach((line) => {
      const cell = document.querySelector(`[data-key="${line._key}"] [data-line-total]`);
      if (cell) cell.textContent = String((line.q1 || 0) + (line.q2 || 0) + (line.q3 || 0) + (line.q4 || 0));
    });
    const totals = sideTotals(ed.side);
    document.querySelectorAll("[data-side-total]").forEach((cell) => {
      cell.textContent = String(totals[cell.dataset.sideTotal] || 0);
    });
    const ourTotal = sideTotals("ours");
    const oppTotal = sideTotals("opponent");
    const us = document.getElementById("rpScoreUs");
    const them = document.getElementById("rpScoreThem");
    if (us) us.textContent = String(ourTotal.total);
    if (them) them.textContent = String(oppTotal.total);
    rpMarkDirty();
  }

  function editorPayload(status) {
    const ed = R.editor;
    return {
      status,
      notes: ed.notes || null,
      sync_score: !!ed.syncScore,
      lines: ed.lines
        .filter((line) => String(line.player_name || "").trim())
        .map((line, index) => ({
          team_side: line.team_side === "opponent" ? "opponent" : "ours",
          player_id: line.team_side === "ours" && line.player_id ? line.player_id : null,
          player_name: String(line.player_name || "").trim(),
          jersey_number: line.jersey_number != null && line.jersey_number !== "" ? Number(line.jersey_number) : null,
          played: line.played !== false,
          q1: clampInt(line.q1),
          q2: clampInt(line.q2),
          q3: clampInt(line.q3),
          q4: clampInt(line.q4),
          fouls: line.fouls != null ? clampInt(line.fouls) : null,
          rebounds: line.rebounds != null ? clampInt(line.rebounds) : null,
          assists: line.assists != null ? clampInt(line.assists) : null,
          steals: line.steals != null ? clampInt(line.steals) : null,
          turnovers: line.turnovers != null ? clampInt(line.turnovers) : null,
          blocks: line.blocks != null ? clampInt(line.blocks) : null,
          minutes: line.minutes != null ? clampInt(line.minutes) : null,
          sort_order: index,
        })),
    };
  }

  async function saveEditor(status) {
    const ed = R.editor;
    if (!ed || ed.saving) return;
    const payload = editorPayload(status);
    if (!payload.lines.length) {
      toast("Aggiungi almeno un giocatore al referto");
      return;
    }
    const missing = ed.lines.find((line) => !String(line.player_name || "").trim() && ((line.q1 || 0) + (line.q2 || 0) + (line.q3 || 0) + (line.q4 || 0)) > 0);
    if (missing) {
      toast("C'è una riga con punti ma senza nome: completa o rimuovila");
      return;
    }
    if (status === "final" && !confirm("Salvare come definitivo? Il referto entrerà nelle statistiche ufficiali.")) return;

    ed.saving = true;
    document.querySelectorAll(".rp-scoreboard__actions .rp-btn").forEach((button) => (button.disabled = true));
    try {
      const result = await rApi(`/api/admin/reports/${ed.matchId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      R.editor = mkEditor(result);
      R.loaded = false;
      toast(status === "final" ? "Referto definitivo salvato" : "Bozza salvata");
      await loadBoard(true);
      await loadStats(true);
      rpRender();
    } catch (error) {
      toast(error.message || "Salvataggio non riuscito");
      ed.saving = false;
      document.querySelectorAll(".rp-scoreboard__actions .rp-btn").forEach((button) => (button.disabled = false));
    }
  }

  async function deleteReport() {
    const ed = R.editor;
    if (!ed?.payload.report.id) return;
    if (!confirm("Eliminare definitivamente questo referto? Il punteggio nel calendario non verrà modificato.")) return;
    try {
      await rApi(`/api/admin/reports/${ed.matchId}`, { method: "DELETE" });
      toast("Referto eliminato");
      R.editor = null;
      R.section = "matches";
      R.loaded = false;
      await loadBoard(true);
      await loadStats(true);
      rpRender();
    } catch (error) {
      toast(error.message || "Eliminazione non riuscita");
    }
  }

  /* ------------------------------- Import -------------------------------- */

  function closeImportModal() {
    const modal = document.getElementById("rpImportModal");
    if (modal) modal.remove();
    R.import = null;
  }

  function openImportModal() {
    if (!R.editor) return;
    R.import = {
      data: null,
      error: null,
      loading: false,
      fileName: "",
      sheetIndex: 0,
      oursIndex: null,
      oppIndex: null,
      resolutions: {},
    };
    const modal = h("div", "rp-modal");
    modal.id = "rpImportModal";
    modal.innerHTML = '<div class="rp-modal__panel" id="rpImportPanel"></div>';
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeImportModal();
    });
    document.body.appendChild(modal);
    requestAnimationFrame(() => modal.classList.add("is-open"));
    renderImport();
  }

  function selectImportSheet(index) {
    const imp = R.import;
    if (!imp?.data) return;
    imp.sheetIndex = index;
    const sheet = imp.data.sheets[index];
    const blocks = sheet?.blocks || [];
    const ours = sheet?.ours_index != null ? sheet.ours_index : blocks.length ? 0 : null;
    const opp = sheet?.opponent_index != null
      ? sheet.opponent_index
      : blocks.length > 1
      ? (ours === 0 ? 1 : 0)
      : null;
    imp.oursIndex = ours;
    imp.oppIndex = opp;
    imp.resolutions = {};
    renderImport();
  }

  function importSheetSide(index, label, total) {
    return `<div class="rp-import-block">
      <div class="rp-import-block__head">
        <strong>${esc(label)}</strong>
        <span class="rp-badge rp-badge--orange">${total} punti</span>
      </div>`;
  }

  function importBlockPreview(sheet, blockIndex, keyPrefix, mode) {
    const block = sheet.blocks[blockIndex];
    if (!block) return '<p class="rp-hint">Nessun blocco selezionato.</p>';
    const players = playerMap();
    const eligible = [...players.values()].sort((a, b) =>
      String(a.last_name || "").localeCompare(String(b.last_name || ""), "it")
    );

    const rows = block.lines
      .map((line, index) => {
        const key = `${keyPrefix}:${blockIndex}:${index}`;
        const confidence = line.confidence || "none";
        const badge = `<span class="rp-conf rp-conf--${esc(confidence)}">${esc(
          confidence === "high" ? "ok" : confidence === "medium" ? "probabile" : confidence === "low" ? "da scegliere" : "nuovo"
        )}</span>`;

        if (mode === "opponent") {
          return `<tr>
            <td>${esc(line.name)}</td>
            <td class="num">${line.jersey_number != null ? line.jersey_number : "—"}</td>
            <td class="num">${line.q1}</td><td class="num">${line.q2}</td>
            <td class="num">${line.q3}</td><td class="num">${line.q4}</td>
            <td class="num strong">${line.total}</td>
          </tr>`;
        }

        const current = R.import.resolutions[key] !== undefined
          ? String(R.import.resolutions[key] ?? "")
          : line.player_id != null
          ? String(line.player_id)
          : "";
        const candidateIds = new Set((line.candidates || []).map((candidate) => candidate.player_id));
        const options = [`<option value="" ${current === "" ? "selected" : ""}>— non abbinato —</option>`];
        (line.candidates || []).forEach((candidate) => {
          options.push(
            `<option value="${candidate.player_id}" ${current === String(candidate.player_id) ? "selected" : ""}>${esc(candidate.name)}${candidate.jersey_number != null ? ` #${candidate.jersey_number}` : ""} · match ${candidate.score}</option>`
          );
        });
        eligible
          .filter((player) => !candidateIds.has(player.id))
          .forEach((player) => {
            options.push(
              `<option value="${player.id}" ${current === String(player.id) ? "selected" : ""}>${esc(player.name)}${player.jersey_number != null ? ` #${player.jersey_number}` : ""}</option>`
            );
          });

        return `<tr>
          <td>${esc(line.name)}<div class="rp-player-sub">${esc(line.matched_name || "")}</div></td>
          <td class="num">${line.jersey_number != null ? line.jersey_number : "—"}</td>
          <td class="num">${line.q1}</td><td class="num">${line.q2}</td>
          <td class="num">${line.q3}</td><td class="num">${line.q4}</td>
          <td class="num strong">${line.total}</td>
          <td>${badge}</td>
          <td><select data-import-resolve="${key}" data-import-player>${options.join("")}</select></td>
        </tr>`;
      })
      .join("");

    const head = mode === "opponent"
      ? "<tr><th>Nome</th><th class='num'>#</th><th class='num'>1Q</th><th class='num'>2Q</th><th class='num'>3Q</th><th class='num'>4Q</th><th class='num'>Tot</th></tr>"
      : "<tr><th>Nome nel file</th><th class='num'>#</th><th class='num'>1Q</th><th class='num'>2Q</th><th class='num'>3Q</th><th class='num'>4Q</th><th class='num'>Tot</th><th>Abbinamento</th><th>Giocatore</th></tr>";

    return `${importSheetSide(blockIndex, mode === "opponent" ? "Avversari" : "CarpeDiem", block.total)}
      <table class="rp-import-table"><thead>${head}</thead><tbody>${rows || "<tr><td colspan='9' class='rp-hint'>Nessun giocatore.</td></tr>"}</tbody></table>
    </div>`;
  }

  function renderImport() {
    const panel = document.getElementById("rpImportPanel");
    if (!panel) return;
    const imp = R.import;
    if (!imp) return;

    const close = `<button class="rp-modal__close" data-import-close aria-label="Chiudi">✕</button>`;
    const head = `<div class="rp-row rp-row--between" style="margin-bottom:14px">
      <div><h3>Importa referto Excel</h3><p class="rp-hint">Carica il file .xlsx dello staff: vengono letti i blocchi squadra e i punti per quarto.</p></div>
      ${close}
    </div>`;

    if (imp.loading) {
      panel.innerHTML = `${head}<div class="rp-skeleton"><div class="rp-skel" style="height:64px"></div><div class="rp-skel" style="height:180px"></div></div>`;
      bindImportCommon();
      return;
    }

    if (!imp.data) {
      panel.innerHTML = `${head}
        ${imp.error ? `<div class="rp-warnbox" style="margin-bottom:12px">⚠️ <span>${esc(imp.error)}</span></div>` : ""}
        <div class="rp-drop" id="rpDrop" role="button" tabindex="0">
          <div style="font-size:2rem;margin-bottom:6px">📄</div>
          <strong>Clicca o trascina qui il file Excel</strong>
          <div class="rp-hint" style="margin-top:4px">Formati supportati: .xlsx, .xlsm · massimo 12 MB</div>
          <input type="file" id="rpFileInput" accept=".xlsx,.xlsm" hidden />
        </div>
        <div class="rp-hint" style="margin-top:12px">Suggerimento: dopo l'importazione controlla gli abbinamenti dei giocatori ambigui e salva il referto.</div>`;
      bindImportCommon();
      return;
    }

    const data = imp.data;
    const sheets = data.sheets || [];
    const sheet = sheets[imp.sheetIndex] || sheets[0];
    if (!sheet) {
      panel.innerHTML = `${head}<div class="rp-warnbox">⚠️ <span>Il file non contiene fogli leggibili.</span></div>`;
      bindImportCommon();
      return;
    }

    const sheetButtons = sheets
      .map(
        (item, index) =>
          `<button class="rp-tab ${index === imp.sheetIndex ? "is-active" : ""}" data-import-sheet="${index}">${esc(item.name)}</button>`
      )
      .join("");

    const blockOptions = (selected) =>
      sheet.blocks
        .map(
          (block, index) =>
            `<option value="${index}" ${selected === index ? "selected" : ""}>Blocco ${index + 1} · ${block.lines.length} giocatori · ${block.total} punti</option>`
        )
        .join("");

    const fields = `<div class="rp-grid rp-grid--2" style="margin-bottom:14px">
      <div class="rp-card">
        <div class="rp-card__title" style="margin-bottom:8px">Blocco CarpeDiem</div>
        <select data-import-ours style="width:100%">
          <option value="">— nessuno —</option>
          ${blockOptions(imp.oursIndex)}
        </select>
        <div class="rp-hint" style="margin-top:8px">Scegli il blocco con i nostri giocatori.</div>
      </div>
      <div class="rp-card">
        <div class="rp-card__title" style="margin-bottom:8px">Blocco avversari</div>
        <select data-import-opp style="width:100%">
          <option value="" ${imp.oppIndex == null ? "selected" : ""}>— nessuno —</option>
          ${blockOptions(imp.oppIndex)}
        </select>
        <div class="rp-hint" style="margin-top:8px">Puoi lasciare vuoto se il file contiene solo i nostri dati.</div>
      </div>
    </div>`;

    const warnings = [...(data.warnings || []), ...(sheet.warnings || [])];
    const warningBox = warnings.length
      ? `<div class="rp-warnbox" style="margin-bottom:12px">⚠️ <div>${warnings.map((warning) => `<div>${esc(warning)}</div>`).join("")}</div></div>`
      : "";

    const previews = `<div class="rp-stack">
      ${imp.oursIndex != null ? importBlockPreview(sheet, imp.oursIndex, `${imp.sheetIndex}`, "ours") : ""}
      ${imp.oppIndex != null ? importBlockPreview(sheet, imp.oppIndex, `${imp.sheetIndex}`, "opponent") : ""}
    </div>`;

    panel.innerHTML = `${head}
      <div class="rp-row rp-row--between" style="margin-bottom:12px">
        <div class="rp-row">
          <span class="rp-badge rp-badge--muted">${esc(imp.fileName)}</span>
          <span class="rp-badge rp-badge--orange">${sheet.blocks.length} blocchi</span>
        </div>
        <button class="rp-btn rp-btn--sm rp-btn--ghost" data-import-reset>← Cambia file</button>
      </div>
      <div class="rp-import-sheet" style="margin-bottom:14px">${sheetButtons}</div>
      ${warningBox}
      ${fields}
      ${previews}
      <div class="rp-row rp-row--between" style="margin-top:18px">
        <button class="rp-btn rp-btn--ghost" data-import-swap ${imp.oppIndex == null ? "disabled" : ""}>⇄ Scambia lati</button>
        <div class="rp-row">
          <button class="rp-btn" data-import-close>Annulla</button>
          <button class="rp-btn rp-btn--primary" data-import-apply>Applica al referto</button>
        </div>
      </div>`;
    bindImportCommon();
  }

  function bindImportCommon() {
    const panel = document.getElementById("rpImportPanel");
    if (!panel) return;
    panel.querySelectorAll("[data-import-close]").forEach((button) => (button.onclick = closeImportModal));

    const drop = document.getElementById("rpDrop");
    const input = document.getElementById("rpFileInput");
    if (drop && input) {
      drop.onclick = () => input.click();
      drop.onkeydown = (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          input.click();
        }
      };
      input.onchange = () => {
        if (input.files?.[0]) handleImportFile(input.files[0]);
      };
      drop.ondragover = (event) => {
        event.preventDefault();
        drop.classList.add("is-drag");
      };
      drop.ondragleave = () => drop.classList.remove("is-drag");
      drop.ondrop = (event) => {
        event.preventDefault();
        drop.classList.remove("is-drag");
        if (event.dataTransfer?.files?.[0]) handleImportFile(event.dataTransfer.files[0]);
      };
    }

    const reset = panel.querySelector("[data-import-reset]");
    if (reset) {
      reset.onclick = () => {
        const fileName = R.import?.fileName || "";
        R.import = {
          data: null,
          error: null,
          loading: false,
          fileName,
          sheetIndex: 0,
          oursIndex: null,
          oppIndex: null,
          resolutions: {},
        };
        renderImport();
      };
    }

    panel.querySelectorAll("[data-import-sheet]").forEach((button) => {
      button.onclick = () => selectImportSheet(Number(button.dataset.importSheet));
    });

    const oursSelect = panel.querySelector("[data-import-ours]");
    if (oursSelect) {
      oursSelect.onchange = () => {
        R.import.oursIndex = oursSelect.value === "" ? null : Number(oursSelect.value);
        renderImport();
      };
    }
    const oppSelect = panel.querySelector("[data-import-opp]");
    if (oppSelect) {
      oppSelect.onchange = () => {
        R.import.oppIndex = oppSelect.value === "" ? null : Number(oppSelect.value);
        renderImport();
      };
    }
    const swap = panel.querySelector("[data-import-swap]");
    if (swap) {
      swap.onclick = () => {
        if (R.import.oppIndex == null) return;
        const ours = R.import.oursIndex;
        R.import.oursIndex = R.import.oppIndex;
        R.import.oppIndex = ours;
        renderImport();
      };
    }

    panel.querySelectorAll("[data-import-resolve]").forEach((select) => {
      select.onchange = () => {
        R.import.resolutions[select.dataset.importResolve] = select.value;
        // Non ridisegniamo tutto: l'abbinamento è già memorizzato.
      };
    });

    const apply = panel.querySelector("[data-import-apply]");
    if (apply) apply.onclick = applyImport;
  }

  async function handleImportFile(file) {
    const imp = R.import;
    if (!imp || !R.editor) return;
    if (!/\.(xlsx|xlsm)$/i.test(file.name)) {
      imp.error = "Formato non supportato: carica un file .xlsx o .xlsm.";
      renderImport();
      return;
    }
    imp.loading = true;
    imp.error = null;
    imp.fileName = file.name;
    renderImport();
    try {
      const form = new FormData();
      form.append("match_id", String(R.editor.matchId));
      form.append("file", file);
      const data = await rApi("/api/admin/reports/parse-excel", { method: "POST", body: form });
      imp.data = data;
      const sheets = data.sheets || [];
      const index = data.suggested_sheet != null && data.suggested_sheet < sheets.length ? data.suggested_sheet : 0;
      imp.sheetIndex = index;
      const sheet = sheets[index];
      const blocks = sheet?.blocks || [];
      imp.oursIndex = sheet?.ours_index != null ? sheet.ours_index : blocks.length ? 0 : null;
      if (sheet?.opponent_index != null) imp.oppIndex = sheet.opponent_index;
      else if (blocks.length > 1 && imp.oursIndex != null) imp.oppIndex = imp.oursIndex === 0 ? 1 : 0;
      else imp.oppIndex = null;
    } catch (error) {
      imp.error = error.message || "Impossibile leggere il file.";
    } finally {
      imp.loading = false;
      renderImport();
    }
  }

  function applyImport() {
    const imp = R.import;
    if (!imp?.data) return;
    const sheet = imp.data.sheets[imp.sheetIndex];
    if (!sheet) return;
    if (imp.oursIndex == null) {
      toast("Seleziona il blocco con i giocatori CarpeDiem");
      return;
    }
    if (imp.oppIndex != null && imp.oppIndex === imp.oursIndex) {
      toast("CarpeDiem e avversari non possono essere lo stesso blocco");
      return;
    }
    if (R.editor.lines.length && !confirm("Sostituire le righe attuali del referto con quelle del file Excel?")) return;

    const players = playerMap();
    const next = [];
    const oursBlock = sheet.blocks[imp.oursIndex];
    (oursBlock?.lines || []).forEach((line, index) => {
      const key = `${imp.sheetIndex}:${imp.oursIndex}:${index}`;
      const resolved = imp.resolutions[key];
      const playerId = resolved !== undefined
        ? resolved === "" ? null : Number(resolved)
        : line.player_id != null
        ? Number(line.player_id)
        : null;
      const player = playerId != null ? players.get(playerId) : null;
      next.push({
        _key: `l${rpSeq++}`,
        team_side: "ours",
        player_id: playerId,
        player_name: player?.name || line.matched_name || line.name,
        jersey_number: line.jersey_number,
        played: true,
        q1: line.q1 || 0,
        q2: line.q2 || 0,
        q3: line.q3 || 0,
        q4: line.q4 || 0,
        sort_order: next.length,
      });
    });

    if (imp.oppIndex != null) {
      const oppBlock = sheet.blocks[imp.oppIndex];
      (oppBlock?.lines || []).forEach((line) => {
        next.push({
          _key: `l${rpSeq++}`,
          team_side: "opponent",
          player_id: null,
          player_name: titleCase(line.name),
          jersey_number: line.jersey_number,
          played: true,
          q1: line.q1 || 0,
          q2: line.q2 || 0,
          q3: line.q3 || 0,
          q4: line.q4 || 0,
          sort_order: next.length,
        });
      });
    }

    if (!next.length) {
      toast("Il blocco selezionato non contiene giocatori");
      return;
    }
    R.editor.lines = next;
    R.editor.side = "ours";
    R.editor.dirty = true;
    closeImportModal();
    rpRender();
    toast(`Importati ${next.length} giocatori dal file Excel`);
  }

  /* --------------------------- Event delegation -------------------------- */

  document.addEventListener("click", (event) => {
    const view = document.getElementById("reportsView");
    if (!view || !view.contains(event.target)) return;

    const playerRow = event.target.closest("[data-rp-player]");
    if (playerRow) {
      event.preventDefault();
      const id = Number(playerRow.dataset.rpPlayer);
      if (!id) return;
      R.section = "players";
      R.playerId = id;
      R.playerDetail = null;
      R.playerLoading = false;
      loadStats().then(() => rpRender());
      return;
    }

    if (event.target.closest("[data-rp-go-matches]")) {
      R.section = "matches";
      rpRender();
      return;
    }

    if (event.target.closest("[data-rp-login]")) {
      if (window.cdShowLogin) window.cdShowLogin("Sessione scaduta: accedi di nuovo.");
      else window.location.reload();
      return;
    }

    if (event.target.closest("[data-rp-retry]")) {
      R.error = null;
      R.loaded = false;
      loadBoard(true).then(() => loadStats(true)).then(() => rpRender());
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (document.getElementById("rpImportModal")) {
      closeImportModal();
      return;
    }
    if (R.editor) {
      const tag = document.activeElement?.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      closeEditor();
    }
  });

  window.addEventListener("beforeunload", (event) => {
    if (R.editor?.dirty) {
      event.preventDefault();
      event.returnValue = "";
    }
  });

  window.renderReports = async function renderReports() {
    if (!state.isStaff) {
      rpRender();
      return;
    }
    if (!R.loaded) {
      await loadBoard();
      if (R.section !== "matches") await loadStats();
    }
    rpRender();
  };
})();
