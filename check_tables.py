import sqlite3
conn = sqlite3.connect('carpediem.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print([r[0] for r in cur.fetchall()])
cur.execute("SELECT sql FROM sqlite_master WHERE name='unavailability'")
row = cur.fetchone()
print(row[0] if row else 'None')
