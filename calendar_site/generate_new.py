import os, sqlite3, json
from collections import defaultdict
from datetime import datetime
from sqlalchemy import create_engine, text

DB = r"C:\HK Studio\Develop\Python\CarpeDiemCalendar\carpediem.db"
OUT = r"C:\HK Studio\Develop\Python\CarpeDiemCalendar\docs\index.html"
OUT_ALT = r"C:\HK Studio\Develop\Python\CarpeDiemCalendar\calendar_site\index.html"

def get_engine():
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url and not url.startswith("sqlite://"):
        # Usa lo stesso DB dell'app (PostgreSQL su Render o locale)
        return create_engine(url, future=True)
    # Altrimenti usa il DB SQLite locale
    return None

def main():
    use_postgres = False
    engine = get_engine()
    conn = None
    cur = None
    rows = []
    if engine is not None:
        use_postgres = True
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT m.id, m.match_date, m.match_time,
                       m.home_team_id, m.away_team_id, m.venue_id,
                       f.code AS fed_code, f.color AS fed_color,
                       ht.name AS home_name, ht.logo_url AS home_logo,
                       at.name AS away_name, at.logo_url AS away_logo,
                       v.name AS venue_name, v.maps_url AS venue_maps,
                       m.competition, m.matchday, m.published,
                       m.home_score, m.away_score
                FROM matches m
                JOIN federations f ON m.federation_id = f.id
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                LEFT JOIN venues v ON m.venue_id = v.id
                WHERE m.published = 1
                ORDER BY m.match_date, m.match_time
            """))
            rows = [dict(r) for r in result.mappings().all()]
    else:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT m.id, m.match_date, m.match_time,
                   m.home_team_id, m.away_team_id, m.venue_id,
                   f.code AS fed_code, f.color AS fed_color,
                   ht.name AS home_name, ht.logo_url AS home_logo,
                   at.name AS away_name, at.logo_url AS away_logo,
                   v.name AS venue_name, v.maps_url AS venue_maps,
                   m.competition, m.matchday, m.published,
                   m.home_score, m.away_score
            FROM matches m
            JOIN federations f ON m.federation_id = f.id
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            LEFT JOIN venues v ON m.venue_id = v.id
            WHERE m.published = 1
            ORDER BY m.match_date, m.match_time
        """)
        rows = cur.fetchall()

    items = []
    for r in rows:
        # Postgres result è già dict; sqlite3 è sqlite3.Row (che si comporta come dict)
        if isinstance(r, dict):
            row = r
        else:
            row = dict(r)
        date_str = row["match_date"]
        time_str = row.get("match_time") or ""
        time_fmt = time_str[:5] if time_str else ""
        venue = row.get("venue_name") or row.get("v_name") or ""
        venue_maps = row.get("venue_maps") or row.get("v_maps_url") or ""
        matchday = row.get("matchday") or ""
        fed = row.get("fed_code")
        color = row.get("fed_color") or ("#2a9fd6" if fed == "CSAIN" else ("#2e9e5b" if fed == "EISI" else "#888"))
        home_name = row.get("home_name")
        away_name = row.get("away_name")
        home_logo = row.get("home_logo") or ""
        away_logo = row.get("away_logo") or ""
        competition = row.get("competition") or ""
        published = row.get("published")
        home_score = row.get("home_score")
        away_score = row.get("away_score")
        is_ours = "CarpeDiem Baskin" in [home_name, away_name]
        opponent = away_name if home_name == "CarpeDiem Baskin" else home_name
        opponent_logo = away_logo if home_name == "CarpeDiem Baskin" else home_logo
        items.append({
            "id": row.get("id"),
            "date": date_str,
            "date_sort": date_str,
            "time": time_fmt,
            "venue": venue,
            "venue_maps": venue_maps,
            "code": f"Giornata {matchday}" if matchday else "",
            "fed": fed,
            "color": color,
            "home": home_name,
            "away": away_name,
            "home_logo": home_logo,
            "away_logo": away_logo,
            "opponent": opponent,
            "opponent_logo": opponent_logo,
            "competition": competition,
            "is_ours_home": home_name == "CarpeDiem Baskin",
            "score": f"{home_score}-{away_score}" if (home_score is not None and away_score is not None) else None,
        })

    # Raggruppa per mese per agenda
    agenda_groups = defaultdict(list)
    for it in items:
        y, m, _ = it["date"].split("-")
        agenda_groups[f"{y}-{m}"].append(it)

    # Prepara dati locali per le icone (convocazioni, indisponibili, passaggi, note)
    local_matches = {}
    for it in items:
        mid = it["id"]
        local_matches[mid] = {"id": mid, "date": it["date"], "convocations": [], "unavailabilities": [], "transport": [], "notes": None}

    if use_postgres:
        # Query su PostgreSQL remoto
        with engine.connect() as conn:
            # Convocazioni
            result = conn.execute(text("SELECT match_id, player_id FROM convocations"))
            for r in result.mappings().all():
                mid = r.get("match_id") or r["match_id"]
                if mid in local_matches:
                    local_matches[mid]["convocations"].append({"player_id": r.get("player_id") or r["player_id"]})
            # Indisponibili
            result = conn.execute(text("SELECT date, player_id FROM unavailability"))
            unavail_by_date = {}
            for r in result.mappings().all():
                d = r.get("date") or r["date"]
                unavail_by_date.setdefault(str(d) if d else None, []).append({"player_id": r.get("player_id") or r["player_id"]})
            for mid, data in local_matches.items():
                if data.get("date") in unavail_by_date:
                    data["unavailabilities"] = unavail_by_date[data["date"]]
            # Passaggi / Note
            result = conn.execute(text("SELECT match_id, kind, driver_id, seats_total, seats_available, notes FROM transport"))
            for r in result.mappings().all():
                mid = r.get("match_id") or r["match_id"]
                if mid in local_matches:
                    local_matches[mid]["transport"].append({
                        "kind": r.get("kind") or r["kind"],
                        "driver_id": r.get("driver_id") or r["driver_id"],
                        "seats_total": r.get("seats_total") or r["seats_total"],
                        "seats_available": r.get("seats_available") or r["seats_available"],
                        "notes": r.get("notes") or r["notes"],
                    })
            # Note match
            result = conn.execute(text("SELECT id, notes FROM matches WHERE notes IS NOT NULL"))
            for r in result.mappings().all():
                mid = r.get("id") or r["id"]
                if mid in local_matches:
                    local_matches[mid]["notes"] = r.get("notes") or r["notes"]
    else:
        # SQLite locale — se vuoto, prova a prendere dati dal server remoto (fallback)
        cur.execute("SELECT c.match_id, c.player_id FROM convocations c")
        for row in cur.fetchall():
            if row["match_id"] in local_matches:
                local_matches[row["match_id"]]["convocations"].append({"player_id": row["player_id"]})
        cur.execute("SELECT u.date, u.player_id FROM unavailability u")
        unavail_by_date = {}
        for row in cur.fetchall():
            unavail_by_date.setdefault(row["date"], []).append({"player_id": row["player_id"]})
        for mid, data in local_matches.items():
            if data.get("date") in unavail_by_date:
                data["unavailabilities"] = unavail_by_date[data["date"]]
        cur.execute("SELECT t.match_id, t.kind, t.driver_id, t.seats_total, t.seats_available, t.notes FROM transport t")
        for row in cur.fetchall():
            if row["match_id"] in local_matches:
                local_matches[row["match_id"]]["transport"].append({"kind": row["kind"], "driver_id": row["driver_id"], "seats_total": row["seats_total"], "seats_available": row["seats_available"], "notes": row["notes"]})
        cur.execute("SELECT id, notes FROM matches WHERE notes IS NOT NULL")
        for row in cur.fetchall():
            if row["id"] in local_matches:
                local_matches[row["id"]]["notes"] = row["notes"]
        # Fallback remoto: se il DB locale è vuoto, prendi dal server
        try:
            import urllib.request
            import urllib.error
            for mid in list(local_matches):
                if not local_matches[mid]["convocations"] and not local_matches[mid]["unavailabilities"] and not local_matches[mid]["transport"]:
                    try:
                        with urllib.request.urlopen(f"https://carpediem-baskin.onrender.com/api/matches/{mid}", timeout=60) as resp:
                            data = json.load(resp)
                            if data.get("convocations"):
                                local_matches[mid]["convocations"] = [{"player_id": c.get("player_id") or c.get("player",{}).get("id")} for c in data["convocations"]]
                            if data.get("unavailabilities"):
                                local_matches[mid]["unavailabilities"] = [{"player_id": u.get("player_id") or u.get("player",{}).get("id")} for u in data["unavailabilities"]]
                            if data.get("transport"):
                                local_matches[mid]["transport"] = data["transport"]
                            if data.get("notes"):
                                local_matches[mid]["notes"] = data["notes"]
                    except Exception:
                        pass
        except Exception:
            pass
    import json
    local_matches_json = json.dumps([local_matches[m] for m in local_matches])

    # ... resto della generazione dell'agenda (uguale a prima) ...
    agenda_groups = defaultdict(list)
    for it in items:
        y, m, _ = it["date"].split("-")
        agenda_groups[f"{y}-{m}"].append(it)

    agenda_html = ""
    for k in sorted(agenda_groups):
        [gy, gm] = k.split("-")
        month_name = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"][int(gm)-1]
        cards = ""
        for it in agenda_groups[k]:
            score_badge = f'<span class="pill result">{it["score"]}</span>' if it["score"] else ""
            venue_link = f'<a href="{it["venue_maps"]}" target="_blank" rel="noopener" class="meta-link">📍 {it["venue"]}</a>' if it["venue_maps"] else f'<span>📍 {it["venue"]}</span>'
            cards += f"""
            <div class="match-card fed-{it['fed']}">
              <div class="match-card__date">
                <div class="match-card__day">{it['date'].split('-')[2]}</div>
                <div class="match-card__mon">{month_name[:3].upper()}</div>
              </div>
              <div class="match-card__main">
                <div class="match-card__titleRow">
                  <img src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/carpediem.png" alt="Carpe Diem" class="match-card__logo" loading="lazy" style="background:#fff;">
                  <span style="font-weight:800;font-size:.95rem;color:var(--text);">Carpe Diem</span>
                  <span class="match-card__vs">vs</span>
                  <img src="{it['opponent_logo']}" alt="{it['opponent']}" class="match-card__logo" loading="lazy" onerror="this.style.display='none'">
                  <span style="font-weight:700;font-size:.95rem;color:var(--text);">{it['opponent']}</span>
                </div>
                <div class="match-card__meta">
                  <span>🕒 {it['time']}</span>
                  <span>{venue_link}</span>
                  <span>🏷 {it['code']}</span>
                </div>
              </div>
              <div class="match-card__right">
                <span class="pill {it['fed']}">{it['fed']}</span>
                {score_badge}
              </div>
              <div class="card-icons" data-match-id="{it['id']}" aria-label="Stato gara {it['id']}">
                <span class="icon-badge" title="Convocazioni" data-type="convocazioni">📋</span>
                <span class="icon-badge" title="Indisponibili" data-type="indisponibili">🚫</span>
                <span class="icon-badge" title="Passaggi" data-type="passaggi">&#129652;</span>
              </div>
            </div>
            """
        agenda_html += f"""
        <section class="agenda-section" aria-label="{month_name} {gy}">
          <h2 class="section-title"><span>{month_name}</span> <small>{gy}</small></h2>
          <div class="agenda-list">
            {cards}
          </div>
        </section>
        """

    calendar_months = defaultdict(lambda: defaultdict(list))
    for it in items:
        y, m, d = it["date"].split("-")
        calendar_months[f"{y}-{m}"][int(d)].append(it)

    calendar_sections = ""
    for k in sorted(calendar_months):
        [gy, gm] = k.split("-")
        month_name = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"][int(gm)-1]
        days_in_month = 31
        grid = ""
        for d in sorted(calendar_months[k]):
            match_days = calendar_months[k][d]
            events = ""
            for it in match_days:
                events += f"""
                <div class="cal-ev fed-{it['fed']}">
                  <span class="cal-badge badge-{it['fed']}">{it['fed']}</span>
                  <div class="cal-ev-time">{it['time']}</div>
                  <div class="cal-ev-vs">{it['home']} <b>vs</b> {it['away']}</div>
                </div>
                """
            grid += f"""
            <div class="cal-cell">
              <div class="cal-day-num">{d}</div>
              <div class="cal-evs">{events}</div>
            </div>
            """
        calendar_sections += f"""
        <section class="cal-section" aria-label="Calendario {month_name} {gy}">
          <h2 class="section-title"><span>📅</span> {month_name} {gy}</h2>
          <div class="cal-month-grid">
            {grid}
          </div>
        </section>
        """

    header_extra = f"""
    <header class="topbar" style="position:sticky;top:0;z-index:30;background:var(--header-bg);border-bottom:3px solid transparent;border-image:linear-gradient(90deg,#8e1b32,#f58220,#12264b) 1;box-shadow:0 2px 8px rgba(18,38,75,.08);padding:14px 20px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
      <div style="display:flex;align-items:center;gap:12px;min-width:0;">
        <img src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/carpediem.png" alt="Carpe Diem" style="height:48px;width:48px;object-fit:contain;border-radius:10px;background:#fff;">
        <div style="line-height:1.1;">
          <div style="font-weight:800;font-size:1.15rem;letter-spacing:.3px;color:var(--text);">CarpeDiem Baskin</div>
          <div style="font-size:.78rem;color:var(--muted);">Calendario impegni squadra — EISI &amp; CSAIN</div>
        </div>
      </div>
      <nav style="display:flex;gap:6px;margin-left:auto;">
        <button onclick="showTab('agenda')" id="tab-agenda" style="padding:8px 16px;border-radius:999px;font-weight:700;font-size:.9rem;text-decoration:none;background:transparent;color:var(--muted);border:1px solid transparent;cursor:pointer;">Agenda</button>
        <button onclick="showTab('calendario')" id="tab-calendario" style="padding:8px 16px;border-radius:999px;font-weight:700;font-size:.9rem;text-decoration:none;background:var(--orange);color:#fff;border:1px solid var(--orange);cursor:pointer;">Calendario</button>
      </nav>
    </header>
    <script>
      function showTab(id) {{
        document.getElementById('agenda').style.display = id === 'agenda' ? 'block' : 'none';
        document.getElementById('calendario').style.display = id === 'calendario' ? 'block' : 'none';
        document.getElementById('tab-agenda').style.background = id === 'agenda' ? 'var(--orange)' : 'transparent';
        document.getElementById('tab-agenda').style.color = id === 'agenda' ? '#fff' : 'var(--muted)';
        document.getElementById('tab-calendario').style.background = id === 'calendario' ? 'var(--orange)' : 'transparent';
        document.getElementById('tab-calendario').style.color = id === 'calendario' ? '#fff' : 'var(--muted)';
      }}
    </script>
    """

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Calendario Carpe Diem</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
  :root {{
    --orange: #f58220; --orange-dark: #d96f16;
    --amaranto: #8e1b32; --navy: #12264b;
    --eisi: #2e9e5b; --csain: #2a9fd6;
    --bg: #f4f6f9; --surface: #ffffff; --surface-2: #f8fafc;
    --text: #14181f; --muted: #5b6472; --border: #e2e6ec; --header-bg: #ffffff;
    --font: "Inter", system-ui, -apple-system, Roboto, Helvetica, Arial, sans-serif;
    --radius: 14px; --radius-sm: 9px;
    --shadow: 0 8px 24px rgba(18,38,75,0.10); --shadow-sm: 0 2px 8px rgba(18,38,75,0.06);
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  html {{ scroll-behavior: smooth; }}
  body {{ font-family: var(--font); background: var(--bg); color: var(--text); line-height: 1.45; padding-bottom: 40px; }}
  a {{ color: var(--orange); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  /* Header */
  .topbar-brand {{ display:flex; align-items:center; gap:12px; min-width:0; }}
  .topbar-brand img {{ height:48px; width:48px; object-fit:contain; border-radius:10px; background:#fff; }}
  .topbar-brand .title {{ font-weight:800; font-size:1.15rem; letter-spacing:.3px; line-height:1.1; }}
  .topbar-brand .subtitle {{ font-size:.78rem; color:var(--muted); }}

  /* Sections */
  .section-title {{ font-size:1.05rem; font-weight:800; text-transform:uppercase; letter-spacing:1px; color:var(--navy); margin: 28px 0 14px; padding-bottom:6px; border-bottom:2px solid var(--orange); display:inline-block; }}
  .agenda-section, .cal-section {{ max-width: 1120px; margin: 0 auto; padding: 18px 18px 0; }}

  /* Agenda Cards */
  .agenda-list {{ display:flex; flex-direction:column; gap:10px; }}
  .match-card {{
    display:flex; align-items:center; gap:14px; background:var(--surface);
    border:1px solid var(--border); border-left:7px solid var(--orange); border-radius:var(--radius);
    padding:14px; cursor:pointer; box-shadow:var(--shadow-sm); transition: transform .12s ease, box-shadow .12s ease;
  }}
  .match-card:hover {{ box-shadow:var(--shadow); transform: translateY(-2px); }}
  .match-card.fed-EISI {{ border-left-color: var(--navy); }}
  .match-card.fed-CSAIN {{ border-left-color: var(--amaranto); }}
  .match-card__date {{ flex:0 0 62px; text-align:center; border-right:1px solid var(--border); padding-right:12px; }}
  .match-card__day {{ font-size:1.6rem; font-weight:800; line-height:1; color:var(--text); }}
  .match-card__mon {{ font-size:.72rem; text-transform:uppercase; color:var(--muted); font-weight:700; letter-spacing:.5px; }}
  .match-card__main {{ flex:1; min-width:0; }}
  .match-card__titleRow {{ display:flex; align-items:center; gap:8px; }}
  .match-card__logo {{ width:30px; height:30px; object-fit:contain; border-radius:6px; flex:0 0 auto; background:#fff; border:1px solid var(--border); padding:2px; }}
  .match-card__vs {{ font-weight:800; font-size:1.02rem; }}
  .match-card__meta {{ font-size:.82rem; color:var(--muted); display:flex; gap:12px; flex-wrap:wrap; margin-top:4px; }}
  .match-card__meta .meta-link {{ color:var(--orange); font-weight:600; }}
  .match-card__right {{ display:flex; flex-direction:column; align-items:flex-end; gap:6px; min-width:64px; }}
  .pill {{ font-size:.68rem; font-weight:800; color:#fff; padding:3px 8px; border-radius:999px; letter-spacing:.3px; }}
  .pill.CSAIN {{ background:var(--csain); }}
  .pill.EISI {{ background:var(--eisi); }}
  .pill.result {{ background:#2e9e5b; }}

  /* Calendario */
  .cal-section h2 {{ margin-top:36px; }}
  .cal-month-grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap:10px; }}
  .cal-cell {{ background:var(--surface-2); border:1px solid var(--border); border-radius:var(--radius-sm); padding:10px; min-height:100px; }}
  .cal-day-num {{ font-size:1.1rem; font-weight:800; color:var(--navy); margin-bottom:6px; }}
  .cal-ev {{ border-left:4px solid var(--orange); background:var(--surface); border-radius:8px; padding:8px; margin-bottom:6px; box-shadow:var(--shadow-sm); }}
  .cal-ev.fed-EISI {{ border-left-color:var(--navy); }}
  .cal-ev.fed-CSAIN {{ border-left-color:var(--amaranto); }}
  .cal-badge {{ font-size:.6rem; font-weight:800; padding:2px 6px; border-radius:5px; color:#fff; display:inline-block; margin-bottom:4px; }}
  .badge-CSAIN {{ background:var(--csain); }}
  .badge-EISI {{ background:var(--eisi); }}
  .cal-ev-time {{ font-weight:800; color:var(--orange); font-size:.82rem; }}
  .cal-ev-vs {{ font-weight:700; font-size:.85rem; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}

  /* Footer */
  footer img {{ height: 28px; opacity: .9; }}
  .card-icons {{ display:flex; gap:6px; margin-top:8px; align-items:center; }}
  .icon-badge {{ font-size:1.1rem; opacity:.25; filter:grayscale(1); transition:opacity .2s, filter .2s; cursor:default; }}
  .icon-badge.active {{ opacity:1; filter:none; cursor:pointer; }}

  /* Responsive */
  @media (max-width: 720px) {{
    .match-card {{ flex-wrap:wrap; gap:10px; padding:12px; }}
    .match-card__date {{ border-right:none; border-bottom:1px solid var(--border); padding:0 0 8px; flex:0 0 100%; text-align:left; display:flex; gap:10px; align-items:center; }}
    .match-card__main {{ min-width:100%; }}
    .cal-month-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
{header_extra}
<div style="max-width:1120px;margin:0 auto;padding:0 18px 40px;">

  <section id="agenda" aria-label="Agenda gare" style="display:block;">
    <h2 class="section-title"><span>📋</span> Agenda</h2>
    {agenda_html}
  </section>

  <section id="calendario" aria-label="Calendario gare" style="display:none;">
    <h2 class="section-title"><span>📅</span> Calendario</h2>
    {calendar_sections}
  </section>

</div>

<footer style="margin-top:40px;padding:22px 18px;background:var(--surface);border-top:2px solid var(--border);text-align:center;color:var(--muted);font-size:.85rem;">
  <div style="display:flex;align-items:center;justify-content:center;gap:24px;flex-wrap:wrap;margin-bottom:8px;">
    <img src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/nbi.png" alt="NBI" style="height:28px;opacity:.9;">
    <img src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/eisi.png" alt="EISI" style="height:28px;opacity:.9;">
    <img src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/csain.png" alt="CSAIN" style="height:28px;opacity:.9;">
  </div>
  <p style="margin:0;color:var(--text);font-weight:600;">Progetto Baskin supportato da <strong>ASD Nuova Basket Isonzo</strong></p>
  <p style="margin:4px 0 8px;font-size:.78rem;color:var(--muted);">Calendario aggiornato dal database dell'app — CSAIN ed EISI</p>
  <button onclick="alert('Per aggiornare la pagina pubblica:\\n1. Esegui: .\\\\.venv\\\\Scripts\\\\python.exe calendar_site\\\\generate.py\\\\n2. Fai push: git add docs/index.html; git commit -m \"update\"; git push')" style="padding:6px 16px;border-radius:999px;background:var(--orange);color:#fff;font-weight:700;border:none;cursor:pointer;">Aggiorna pagina pubblica</button>
</footer>

<script>
  const LOCAL_MATCHES = {local_matches_json};
  document.querySelectorAll('.card-icons[data-match-id]').forEach((box) => {{
    const id = box.getAttribute('data-match-id');
    const m = (LOCAL_MATCHES || []).find((x) => String(x.id) === String(id));
    try {{
      const convBadge = box.querySelector('.icon-badge[data-type="convocazioni"]');
      const unavBadge = box.querySelector('.icon-badge[data-type="indisponibili"]');
      const passBadge = box.querySelector('.icon-badge[data-type="passaggi"]');
      if (convBadge && (m?.convocations || []).length) {{
        convBadge.classList.add('active'); convBadge.title = (m.convocations || []).length + ' convocati';
      }} else if (convBadge) {{ convBadge.classList.remove('active'); }}
      if (unavBadge && (m?.unavailabilities || []).length) {{
        unavBadge.classList.add('active'); unavBadge.title = (m.unavailabilities || []).length + ' indisponibili';
      }} else if (unavBadge) {{ unavBadge.classList.remove('active'); }}
      if (passBadge && ((m?.transport || []).length || (m?.notes && m.notes.trim()))) {{
        passBadge.classList.add('active'); passBadge.title = m.notes || 'Passaggio presente';
      }} else if (passBadge) {{ passBadge.classList.remove('active'); }}
    }} catch (e) {{ }}
  }});
</script>

</body>
</html>"""

    if not use_postgres:
        conn.close()

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    with open(OUT_ALT, "w", encoding="utf-8") as f:
        f.write(html)
    print("Generato pagina statica con icone locali:", OUT)

if __name__ == "__main__":
    main()
