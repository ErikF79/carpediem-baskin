import sqlite3
conn = sqlite3.connect('C:\\HK Studio\\Develop\\Python\\CarpeDiemCalendar\\carpediem.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
for r in c.fetchall():
    print(r)
