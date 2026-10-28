import sqlite3
from datetime import date, time

conn = sqlite3.connect('carpediem.db')
c = conn.cursor()

# Aggiungi venue mancanti
venues = [
    ("Pala Macoratti -Gradisca-", None, "https://maps.google.com/?q=Pala+Macoratti+Gradisca"),
    ("Cividale", None, "https://maps.google.com/?q=Cividale"),
    ("Gorizia", None, "https://maps.google.com/?q=Gorizia"),
    ("Pordenone - PalaMarson", None, "https://maps.google.com/?q=PalaMarson+Pasiano"),
]
for v in venues:
    c.execute("INSERT OR IGNORE INTO venues (name, address, maps_url) VALUES (?,?,?)", v)

# Recupera id nuove venue
c.execute("SELECT id, name FROM venues WHERE name = ?", ("Pala Macoratti -Gradisca-",))
venue_gradisca = c.fetchone()[0]

# Correggi CSAIN
updates = [
    (4, "2027-01-10", "10:30:00", 6, 1, 1),  # D04 Latisana
    (5, "2027-02-07", "17:30:00", 1, 9, 5),  # D08 Turriaco casa Carpe Diem
    (6, "2027-02-21", "15:30:00", 3, 1, 4),  # D09 Trieste
    (7, "2027-03-21", "11:30:00", 5, 1, 3),  # D11 Muggia Baskin Tolmezzo
    (8, "2027-04-04", "15:30:00", 1, 8, 5),  # D12 Turriaco
    (9, "2027-04-18", "11:30:00", 1, 10, venue_gradisca),  # D13 Gradisca
    (10, "2027-05-02", "09:30:00", 12, 1, 2),  # D14 Monfalcone 02/05
    (11, "2027-05-16", "11:30:00", 1, 11, 2),  # D15 Monfalcone
]
for mid, d, tm, home_id, away_id, venue_id in updates:
    c.execute("UPDATE matches SET match_date=?, match_time=?, home_team_id=?, away_team_id=?, venue_id=? WHERE id=?", (d, tm, home_id, away_id, venue_id, mid))
    # Se cambia ente? No, CSAIN resta id=2
    c.execute("UPDATE matches SET federation_id=2 WHERE id=?", (mid,))

# Aggiungi gare EISI (federation_id=1)
eisi = [
    ("2026-11-15", "17:30:00", 19, 1, 6, 1),  # G1 Cividale? No, Cividale come luogo, ma venue non esiste ancora. Useremo venue generica per Cividale (id 21 dopo insert)
]
# Recupera id Cividale venue
c.execute("SELECT id FROM venues WHERE name = ?", ("Cividale",))
venue_cividale = c.fetchone()[0]

eisi_matches = [
    ("2026-11-15", "17:30:00", 18, 1, venue_cividale, 1),  # G1 Tiger Baskin GO (18) vs Carpe Diem, Cividale
    ("2026-11-22", "17:30:00", 1, 11, 5, 1),  # G2 Turriaco Carpe Diem vs Boom Baskin
    ("2026-12-20", "11:30:00", 1, 14, 1, 1),  # G3 Latisana Carpe Diem vs Kros Over Pordenone
    ("2027-01-10", "09:30:00", 1, 19, 6, 1),  # G4 Gorizia Carpe Diem vs Trieste All IN
    ("2027-01-17", "17:30:00", 1, 18, 5, 1),  # G5 Turriaco Carpe Diem vs Tiger Baskin GO
    ("2027-01-31", "11:30:00", 11, 1, 7, 1),  # G6 Pordenone Boom Baskin vs Carpe Diem (PalaMarson venue id 7?)
    ("2027-02-28", "11:30:00", 14, 1, 1, 1),  # G7 Latisana Kros Over Pordenone vs Carpe Diem
    ("2027-03-07", "09:30:00", 19, 1, 4, 1),  # G8 Trieste Trieste All IN vs Carpe Diem
]
# Recupera id PalaMarson
c.execute("SELECT id FROM venues WHERE name = ?", ("Pordenone - PalaMarson",))
venue_pala = c.fetchone()[0]
# Recupera id Gorizia
c.execute("SELECT id FROM venues WHERE name = ?", ("Gorizia",))
venue_gorizia = c.fetchone()[0]

# Correggo eisi_matches con venue corrette
# G1: Cividale (venue_cividale)
# G2: Turriaco (5)
# G3: Latisana (1)
# G4: Gorizia (venue_gorizia)
# G5: Turriaco (5)
# G6: Pordenone PalaMarson (venue_pala)
# G7: Latisana (1)
# G8: Trieste (4)
eisi_final = [
    ("2026-11-15", "17:30:00", 18, 1, venue_cividale, "G1", 1, True),
    ("2026-11-22", "17:30:00", 1, 11, 5, "G2", 1, True),
    ("2026-12-20", "11:30:00", 1, 14, 1, "G3", 1, True),
    ("2027-01-10", "09:30:00", 1, 19, venue_gorizia, "G4", 1, True),
    ("2027-01-17", "17:30:00", 1, 18, 5, "G5", 1, True),
    ("2027-01-31", "11:30:00", 11, 1, venue_pala, "G6", 1, True),
    ("2027-02-28", "11:30:00", 14, 1, 1, "G7", 1, True),
    ("2027-03-07", "09:30:00", 19, 1, 4, "G8", 1, True),
]

for d, tm, home_id, away_id, venue_id, code, fed_id, pub in eisi_final:
    c.execute("""INSERT INTO matches (match_date, match_time, federation_id, home_team_id, away_team_id, venue_id, competition, matchday, published) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (d, tm, fed_id, home_id, away_id, venue_id, "Campionato EISI 2026/2027", int(code[1:]), pub))

conn.commit()
print("Aggiornato DB")
