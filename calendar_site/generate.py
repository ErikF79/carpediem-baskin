import sqlite3
from collections import defaultdict
from datetime import datetime

DB = r"C:\HK Studio\Develop\Python\CarpeDiemCalendar\carpediem.db"
OUT = r"C:\HK Studio\Develop\Python\CarpeDiemCalendar\docs/index.html"
OUT_ALT = r"C:\HK Studio\Develop\Python\CarpeDiemCalendar\calendar_site/index.html"

def main():
    # Copia templates/index.html e sostituisci i percorsi con quelli remoti
    with open("templates/index.html", "r", encoding="utf-8") as f:
        app_html = f.read()
    app_html = app_html.replace('href="/static/css/style.css?v=17"', 'href="https://carpediem-baskin.onrender.com/static/css/style.css?v=17"')
    app_html = app_html.replace('src="/static/assets/carpediem.png"', 'src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/carpediem.png"')
    app_html = app_html.replace('src="/static/assets/nbi.png"', 'src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/nbi.png"')
    app_html = app_html.replace('src="/static/assets/eisi.png"', 'src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/eisi.png"')
    app_html = app_html.replace('src="/static/assets/csain.png"', 'src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/csain.png"')
    app_html = app_html.replace('href="/manifest.webmanifest"', 'href="https://carpediem-baskin.onrender.com/manifest.webmanifest"')
    app_html = app_html.replace('href="/sw.js"', 'href="https://carpediem-baskin.onrender.com/sw.js"')
    app_html = app_html.replace('src="/static/js/app.js?v=17"', 'src="https://carpediem-baskin.onrender.com/static/js/app.js?v=17"')
    app_html = app_html.replace('src="/static/js/admin.js?v=17"', 'src="https://carpediem-baskin.onrender.com/static/js/admin.js?v=17"')
    # Inserisci il link al DB remoto prima del primo script
    app_html = app_html.replace('<script src="https://carpediem-baskin.onrender.com/static/js/app.js?v=17">', '<script>window.CarpeDiemAPI = "https://carpediem-baskin.onrender.com";</script>\n  <script src="https://carpediem-baskin.onrender.com/static/js/app.js?v=17">')
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(app_html)
    print("Generato app remota:", OUT)

if __name__ == "__main__":
    main()
