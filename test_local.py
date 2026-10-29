import json, re
with open('docs/index.html', 'r', encoding='utf-8') as f:
    s = f.read()
start = s.find('const LOCAL_MATCHES')
end = s.find('];', start)
text = s[start:end+2].replace('const LOCAL_MATCHES =', '')
data = json.loads(text)
print('Total matches:', len(data))
print('Match 1 conv:', len(data[0]['convocations']), 'unav:', len(data[0]['unavailabilities']), 'notes:', data[0]['notes'])
print('Match 2 conv:', len(data[1]['convocations']))
