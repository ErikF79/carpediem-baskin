import sqlite3
conn = sqlite3.connect('carpediem.db')
c = conn.cursor()
c.execute("UPDATE venues SET name='Palestra Bearzi - Zio Pino', maps_url='https://maps.google.com/?q=Palestra+Bearzi+Udine' WHERE id=6")
conn.commit()
print('Udine aggiornata')
