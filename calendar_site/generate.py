"""Genera la pagina pubblica in docs/.

La pagina è una copia dell'app con:
  * CSS/JS/immagini copiati in locale (nessuna dipendenza dal backend per l'aspetto);
  * uno snapshot dei dati (data.json) così i contenuti sono sempre visibili,
    anche quando il backend è spento o in avvio;
  * l'API remota impostata in window.CarpeDiemAPI: se il backend risponde,
    i dati vengono aggiornati in tempo reale.
  * gli album fotografici della stagione (opzionali) presi da albums.json.

Uso:  python calendar_site/generate.py
"""

import json
import re
import shutil
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "index.html"
DOCS = ROOT / "docs"
STATIC = ROOT / "static"
SITE = "https://carpediem-baskin.onrender.com"
ALBUMS_FILE = ROOT / "albums.json"


def fetch_json(path: str, timeout: int = 120):
    with urllib.request.urlopen(SITE + path, timeout=timeout) as resp:
        return json.load(resp)


def copy_static() -> None:
    """Copia CSS, JS e immagini accanto alla pagina pubblica."""
    target = DOCS / "static"
    if target.exists():
        shutil.rmtree(target)
    (target / "js").mkdir(parents=True)
    shutil.copytree(STATIC / "css", target / "css")
    shutil.copytree(STATIC / "assets", target / "assets")
    shutil.copy2(STATIC / "js" / "app.js", target / "js" / "app.js")


def load_albums() -> list[dict]:
    if not ALBUMS_FILE.exists():
        return []
    try:
        data = json.loads(ALBUMS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as exc:
        print(f"albums.json non valido ({exc}): album ignorati")
        return []


def build_snapshot() -> dict:
    config = fetch_json("/api/config")
    matches = fetch_json("/api/matches")
    players = fetch_json("/api/players")

    details = {}
    for match in matches:
        if (
            match.get("has_convocations")
            or match.get("has_unavailabilities")
            or match.get("has_transport")
        ):
            details[str(match["id"])] = fetch_json(f"/api/matches/{match['id']}")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": config,
        "matches": matches,
        "players": players,
        "details": details,
        "albums": load_albums(),
    }


def build_html() -> str:
    html = TEMPLATE.read_text(encoding="utf-8")

    # Pagina pubblica: risorse locali, niente area staff.
    html = html.replace('href="/static/', 'href="static/')
    html = html.replace('src="/static/', 'src="static/')
    html = re.sub(r'\s*<link rel="manifest"[^>]*>', "", html)
    html = re.sub(r'\s*<link rel="apple-touch-icon"[^>]*>', "", html)
    html = re.sub(r'\s*<script src="static/js/admin\.js[^"]*"></script>', "", html)

    # API remota + modalità pubblica, prima di app.js
    html, n = re.subn(
        r'(?m)^(\s*)<script src="static/js/app\.js',
        rf'\1<script>window.CarpeDiemAPI = "{SITE}"; window.CarpeDiemPublic = true;</script>\n'
        rf'\1<script src="static/js/app.js',
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit('Tag <script src="static/js/app.js"> non trovato nel template')

    return html


def main() -> None:
    snapshot_path = DOCS / "data.json"
    previous = snapshot_path.read_text(encoding="utf-8") if snapshot_path.exists() else None

    copy_static()
    (DOCS / "index.html").write_text(build_html(), encoding="utf-8")

    try:
        snapshot = build_snapshot()
    except Exception as exc:  # backend spento o irraggiungibile
        if previous:
            print(f"Backend non raggiungibile ({exc}): mantengo lo snapshot precedente.")
        else:
            print(f"Backend non raggiungibile ({exc}): nessuno snapshot disponibile.")
            sys.exit(1)
    else:
        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"Snapshot: {len(snapshot['matches'])} gare, "
            f"{len(snapshot['players'])} giocatori, "
            f"{len(snapshot['details'])} dettagli, "
            f"{len(snapshot['albums'])} album."
        )

    print("Pagina pubblica generata in:", DOCS)


if __name__ == "__main__":
    main()
