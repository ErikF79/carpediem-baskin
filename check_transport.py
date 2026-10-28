import sqlite3
conn = sqlite3.connect('carpediem.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transport'")
print('Tabella transport:', c.fetchone())
