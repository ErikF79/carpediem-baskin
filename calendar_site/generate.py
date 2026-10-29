"""Genera docs/index.html: copia di templates/index.html con risorse e API remote.

La pagina pubblica (GitHub Pages) usa lo stesso codice dell'app ma carica
CSS/JS/immagini dal backend su Render e punta le API all'origine remota.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "index.html"
OUT = ROOT / "docs" / "index.html"
SITE = "https://carpediem-baskin.onrender.com"


def main() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")

    # API remota: deve essere definita prima di app.js
    html, n = re.subn(
        r'(?m)^(\s*)<script src="/static/js/app\.js',
        rf'\1<script>window.CarpeDiemAPI = "{SITE}";</script>\n\1<script src="/static/js/app.js',
        html,
        count=1,
    )
    if n != 1:
        raise SystemExit("Tag <script src=\"/static/js/app.js\"> non trovato nel template")

    # Risorse statiche servite dal backend
    html = html.replace('href="/static/', f'href="{SITE}/static/')
    html = html.replace('src="/static/', f'src="{SITE}/static/')
    html = html.replace('href="/manifest.webmanifest"', f'href="{SITE}/manifest.webmanifest"')
    html = html.replace('href="/sw.js"', f'href="{SITE}/sw.js"')

    OUT.write_text(html, encoding="utf-8")
    print("Generato app remota:", OUT)


if __name__ == "__main__":
    main()
