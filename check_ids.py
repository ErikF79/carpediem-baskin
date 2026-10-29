import re
with open('templates/index.html', 'r', encoding='utf-8') as f:
    s = f.read()
ids = re.findall(r'(?:section|main|footer|header)[^>]*id="([^"]+)"', s)
print('Ids:', ids)
for x in ['calendarView', 'agendaView', 'rosterView', 'adminView', 'staffTab']:
    print(x, x in s)
print('Total length:', len(s))
