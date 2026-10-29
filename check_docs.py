with open('docs/index.html', 'r', encoding='utf-8') as f:
    s = f.read()
for x in ['calendarView', 'agendaView', 'rosterView', 'adminView',
          'calendar__grid', 'cal-dow', 'cal-cell', 'cal-day-num',
          'agenda-section', 'match-card', 'card-icons', 'icon-badge',
          'window.CarpeDiemAPI', 'calendar-section', 'cal-section',
          'cal-badge', 'cal-ev-time', 'cal-ev-vs']:
    print(x, ':', x in s)
print('Length:', len(s))
