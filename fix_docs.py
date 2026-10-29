with open('templates/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

replaces = {
    'href="/static/css/style.css?v=17"': 'href="https://carpediem-baskin.onrender.com/static/css/style.css?v=17"',
    'src="/static/assets/carpediem.png"': 'src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/carpediem.png"',
    'src="/static/assets/nbi.png"': 'src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/nbi.png"',
    'src="/static/assets/eisi.png"': 'src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/eisi.png"',
    'src="/static/assets/csain.png"': 'src="https://raw.githubusercontent.com/ErikF79/carpediem-baskin/main/static/assets/csain.png"',
    'href="/manifest.webmanifest"': 'href="https://carpediem-baskin.onrender.com/manifest.webmanifest"',
    'href="/sw.js"': 'href="https://carpediem-baskin.onrender.com/sw.js"',
    'src="/static/js/app.js?v=17"': 'src="https://carpediem-baskin.onrender.com/static/js/app.js?v=17"',
    'src="/static/js/admin.js?v=17"': 'src="https://carpediem-baskin.onrender.com/static/js/admin.js?v=17"',
}

for old, new in replaces.items():
    html = html.replace(old, new)

# Inserisci il link al DB remoto
old_script = '<script src="https://carpediem-baskin.onrender.com/static/js/app.js?v=17">'
new_script = '<script>window.CarpeDiemAPI = "https://carpediem-baskin.onrender.com";</script>\n  <script src="https://carpediem-baskin.onrender.com/static/js/app.js?v=17">'
html = html.replace(old_script, new_script)

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('docs/index.html aggiornato')
