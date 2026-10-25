import sqlite3
from datetime import datetime

DB = r"C:\HK Studio\Develop\Python\CarpeDiemCalendar\carpediem.db"
OUT = r"C:\HK Studio\Develop\Python\CarpeDiemCalendar\calendar_site\index.html"

def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, m.match_date, m.match_time,
               f.code AS fed_code, f.color AS fed_color,
               m.home_team_id, m.away_team_id, m.venue_id,
               ht.name AS home_name, at.name AS away_name,
               v.name AS venue_name, m.competition, m.matchday
        FROM matches m
        JOIN federations f ON m.federation_id = f.id
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        LEFT JOIN venues v ON m.venue_id = v.id
        WHERE m.published = 1
        ORDER BY m.match_date, m.match_time
    """)
    rows = cur.fetchall()
    conn.close()

    items = []
    for r in rows:
        date_str = r["match_date"]
        time_str = r["match_time"] or ""
        time_fmt = time_str[:5] if time_str else ""
        venue = r["venue_name"] or ""
        matchday = r["matchday"] or ""
        fed = r["fed_code"]
        color = r["fed_color"] or "#888"
        items.append({
            "date": date_str,
            "time": time_fmt,
            "venue": venue,
            "code": matchday,
            "fed": fed,
            "color": color,
            "home": r["home_name"],
            "away": r["away_name"],
        })

    html_items = "\n".join(f"""
    <article class="card">
      <div class="tag" style="background:{it['color']}">{it['fed']}</div>
      <h3>{it['date']} <span class="time">{it['time']}</span></h3>
      <p class="venue">{it['venue']} — {it['code']}</p>
      <div class="teams">
        <b>{it['home']}</b> <span class="vs">vs</span> <b>{it['away']}</b>
      </div>
    </article>
""" for it in items)

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Calendario Carpe Diem</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
  :root {{
    --bg:#0b0c15; --surface:#12132e; --text:#f0f0f5; --muted:#a0a0b0;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Inter',system-ui,sans-serif; background:var(--bg); color:var(--text); padding:2rem 1rem; }}
  .container {{ max-width:720px; margin:0 auto; }}
  header {{ text-align:center; margin-bottom:2.5rem; }}
  h1 {{ font-size:2rem; letter-spacing:-0.02em; }}
  .subtitle {{ color:var(--muted); margin-top:.25rem; }}
  .grid {{ display:grid; gap:1.25rem; }}
  .card {{ background:var(--surface); border-radius:1rem; padding:1.25rem 1.5rem; position:relative; box-shadow:0 10px 30px rgba(0,0,0,.35); border:1px solid rgba(255,255,255,.05); }}
  .tag {{ position:absolute; top:-.6rem; right:1.25rem; padding:.25rem .75rem; border-radius:999px; font-size:.75rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:#fff; box-shadow:0 4px 12px rgba(0,0,0,.4); }}
  h3 {{ font-size:1.1rem; margin-bottom:.25rem; }}
  .time {{ color:var(--muted); font-weight:400; margin-left:.5rem; }}
  .venue {{ color:var(--muted); font-size:.9rem; margin-bottom:.5rem; }}
  .teams {{ display:flex; align-items:center; gap:.75rem; font-size:1.05rem; margin-top:.5rem; }}
  .vs {{ color:var(--muted); font-size:.85rem; }}
  @media (max-width: 480px) {{ .card {{ padding:1rem; }} }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Calendario Carpe Diem</h1>
    <p class="subtitle">Aggiornato dal database dell'app — CSAIN ed EISI</p>
  </header>
  <main class="grid">
    {html_items}
  </main>
</div>
</body>
</html>"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("Generato:", OUT)

if __name__ == "__main__":
    main()
