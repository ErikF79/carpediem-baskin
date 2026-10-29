with open('calendar_site/generate.py', 'r', encoding='utf-8') as f:
    content = f.read()
start = content.find('<script>\n  // Per ogni card')
end = content.find('</script>', start) + len('</script>')
new_block = '<script>\n  const LOCAL_MATCHES = {local_matches_json};\n  document.querySelectorAll(\'.card-icons[data-match-id]\').forEach((box) => {{\n    const id = box.getAttribute(\'data-match-id\');\n    const m = (LOCAL_MATCHES || []).find((x) => String(x.id) === String(id));\n    try {{\n      const convBadge = box.querySelector(\'.icon-badge[data-type="convocazioni"]\');\n      const unavBadge = box.querySelector(\'.icon-badge[data-type="indisponibili"]\');\n      const passBadge = box.querySelector(\'.icon-badge[data-type="passaggi"]\');\n      if (convBadge && (m?.convocations || []).length) {{\n        convBadge.classList.add(\'active\'); convBadge.title = (m.convocations || []).length + \' convocati\';\n      }} else if (convBadge) {{ convBadge.classList.remove(\'active\'); }}\n      if (unavBadge && (m?.unavailabilities || []).length) {{\n        unavBadge.classList.add(\'active\'); unavBadge.title = (m.unavailabilities || []).length + \' indisponibili\';\n      }} else if (unavBadge) {{ unavBadge.classList.remove(\'active\'); }}\n      if (passBadge && ((m?.transport || []).length || (m?.notes && m.notes.trim()))) {{\n        passBadge.classList.add(\'active\'); passBadge.title = m.notes || \'Passaggio presente\';\n      }} else if (passBadge) {{ passBadge.classList.remove(\'active\'); }}\n    }} catch (e) {{ }}\n  }});\n  </script>'
content = content[:start] + new_block + content[end:]
with open('calendar_site/generate.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Replaced successfully')
