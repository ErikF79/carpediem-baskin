import sqlite3
conn = sqlite3.connect('carpediem.db')
cur = conn.cursor()
cur.execute("SELECT * FROM convocations WHERE match_id=1")
print('Conv:', cur.fetchall())
cur.execute("SELECT * FROM unavailability WHERE date='2026-11-01'")
print('Unav:', cur.fetchall())
cur.execute("SELECT * FROM transport WHERE match_id=1")
print('Trans:', cur.fetchall())
