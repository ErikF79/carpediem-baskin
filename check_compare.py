import os
for f in ['templates/index.html', 'docs/index.html']:
    p = os.path.join('.', f)
    size = os.path.getsize(p)
    print(f'{f}: {size} bytes')

# Controlla se templates/index.html è tagliato
with open('templates/index.html', 'r', encoding='utf-8') as f:
    t = f.read()
with open('docs/index.html', 'r', encoding='utf-8') as f:
    d = f.read()

# Controlla se contains AGENDA CONTENT OR MES DI JAVASCRIPT
print()
for x in ['agendaView', 'calendarView', 'rosterView', 'adminView',
          'calendar__grid', 'cal-dow', 'app.matches:', 'window.CarpeDiemAPI',
          'calendarView content', 'agendaView content']:
    print(f'templates:{x}:', x in t)
    print(f'docs:{x}:', x in d)
