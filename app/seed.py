"""Popola il database con i dati iniziali (rosa di esempio + calendario CSAIN).

Uso:
    py -m app.seed          # popola solo se vuoto
    py -m app.seed reset    # svuota e ricrea tutto
"""
from datetime import date, time
import sys

from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import Federation, Match, Player, Team, Venue

LOGO = "/static/assets"
OUR_TEAM = "Carpe Diem"

# Calendario CSAIN (fornito dallo staff)
# (data, ora, citta/palestra, codice giornata, squadra_casa, squadra_ospite)
CSAIN_MATCHES = [
    ("2026-11-01", time(9, 30), "Palestra Bearzi - Zio Pino", "D01", "Zio Pino Kobe", OUR_TEAM),
    ("2026-11-15", time(9, 30), "Palestra Muggia", "D02", "Baskinterclub Muggia", OUR_TEAM),
    ("2026-11-29", time(11, 30), "Palestra Bearzi - Zio Pino", "D03", "Zio Pio Cainero", OUR_TEAM),
    ("2027-01-10", time(10, 30), "Palestra Latisana", "D04", "Fra Mille Colori", OUR_TEAM),
    ("2027-02-07", time(17, 30), "Palestra Turriaco", "D08", OUR_TEAM, "Zio Pino Magic"),
    ("2027-02-21", time(15, 30), "Palestra Trieste", "D09", "Bazinga", OUR_TEAM),
    ("2027-03-21", time(11, 30), "Palestra Muggia", "D11", "Baskin Tolmezzo", OUR_TEAM),
    ("2027-04-04", time(15, 30), "Palestra Turriaco", "D12", OUR_TEAM, "Zio Pino Moki"),
    ("2027-04-18", time(11, 30), "Pala Macoratti -Gradisca-", "D13", OUR_TEAM, "Baskin4TS"),
    ("2027-05-02", time(9, 30), "Palestra Monfalcone", "D14", "Go Beyond", OUR_TEAM),
    ("2027-05-16", time(11, 30), "Palestra Monfalcone", "D15", OUR_TEAM, "Boom Latisana"),
]

# Anagrafica squadre dei due campionati
CSAIN_TEAMS = [
    "Zio Pino Kobe",
    "Bazinga",
    "Baskinterclub Muggia",
    "Baskin Tolmezzo",
    "Fra Mille Colori",
    "Zio Pio Cainero",
    "Zio Pino Moki",
    "Zio Pino Magic",
    "Baskin4TS",
    "Boom Latisana",
    "Go Beyond",
]
EISI_TEAMS = [
    "UBC Baskin",
    "Kros Over 1",
    "Kros Over 2",
    "Kros Over 3",
    "Gonars",
    "Tigers Goriziana",
    "Trieste All IN",
    "Cividale",
    "Boom Latisana",
]

EISI_MATCHES = [
    ("2026-11-15", time(17, 30), "Cividale", "G1", "Tigers Goriziana", OUR_TEAM),
    ("2026-11-22", time(17, 30), "Palestra Turriaco", "G2", OUR_TEAM, "Boom Latisana"),
    ("2026-12-20", time(11, 30), "Palestra Latisana", "G3", OUR_TEAM, "Kros Over 1"),
    ("2027-01-10", time(9, 30), "Gorizia", "G4", OUR_TEAM, "Trieste All IN"),
    ("2027-01-17", time(17, 30), "Palestra Turriaco", "G5", OUR_TEAM, "Tigers Goriziana"),
    ("2027-01-31", time(11, 30), "Pordenone - PalaMarson", "G6", "Boom Latisana", OUR_TEAM),
    ("2027-02-28", time(11, 30), "Palestra Latisana", "G7", "Kros Over 1", OUR_TEAM),
    ("2027-03-07", time(9, 30), "Palestra Trieste", "G8", "Trieste All IN", OUR_TEAM),
]

# Squadre associate a entrambi i campionati (Latisana EISI = Boom Latisana CSAIN)
TEAMS_BOTH = ["Boom Latisana"]

# Loghi squadre (dal repository foto Baskin)
TEAM_LOGOS = {
    "Baskin Tolmezzo": "https://lh3.googleusercontent.com/pw/AP1GczOSGEBjnYfjWN0ixugTTcmIaU1a_YcD83LtqymBwEp2LQTUf3L2wIzRix_VqWe-TytamQlUqIF7SVq6RvSkZiXt1bEPoERynyWq2RroJc1tpUUEfwRoDirFo-UNN0eryKZH4sMfpTvnkw98bp1gzgs=w277-h336-s-no-gm?authuser=0",
    "Baskin4TS": "https://lh3.googleusercontent.com/pw/AP1GczNEZNgOtDRUeLUTv8ndUtdRx3Vgt-DmbMQyOV0WOeMr3Aru2iADis4l5E4tGKvlIa5VSAmtEMpWwysgGTJiLgyavCMEN_752hn1M2l4GXoX_qMemzyr4OvizhFnS77MKxECYNRoh4OOCrO8ch9VJKA7=w225-h225-s-no-gm?authuser=0",
    "Baskinterclub Muggia": "https://lh3.googleusercontent.com/pw/AP1GczNcUCKV-3KEi2Sok1vEowIhiJ3RI052oMOKuTpKAHp87y75b44NO6scMFRcfZFZnbrUuZTNitOhuSUaENT4buPKHxfmSQuWeCb6EEtUcQ0sdvggxoYUeMnUMZ_Ft1Ei0MJ3N14AeN9JRTpDk1yiiLh9=w422-h333-s-no-gm?authuser=0",
    "Bazinga": "https://lh3.googleusercontent.com/pw/AP1GczN6Cvbo-v-F4ntJlrb3_L-R6DCXU7WyVSIBJUECuylMAfaPNQisUtz4WudI7hEIXQxlXf2BBj5vgG50uAnH-SMIl3q8458_dUTD93tejupuHY33OfqOlG1MVNgvwJIP90tJJCvU1auPLJNEcigbUVHH=w584-h406-s-no-gm?authuser=0",
    "Boom Latisana": "https://lh3.googleusercontent.com/pw/AP1GczPtvxmt_b1qhNGrAjq6CzEJYu3UvCVktqJsxnhnrg-fbw0G8GacKPdt5lrszXALmU5BO1-xO48pE9MArmJIVWoqx5tp3_G_n_IlpOxl6Z97eUtORXt6B6ejcDCJlU499nAJuS7T6wZe2_pU2QzfLurk=w280-h135-s-no-gm?authuser=0",
    "Cividale": "https://lh3.googleusercontent.com/pw/AP1GczMiri8SOtvywJrqMmrR7wLc_REjgFs8IqU-gMUK2me7eE7rPn_sJWHm4LMrVAGv6rMSPJf9SquhEvdFtu6S-834aZxBYQnrNKpymxlX7YBeazHUAzF_EM5lFXKdatF_Wxfb6JPLwy_PtsSHzHAID6xK=w200-h168-s-no-gm?authuser=0",
    "Fra Mille Colori": "https://lh3.googleusercontent.com/pw/AP1GczMfEZivsE8pIvDhcE4LaibMUwLgrpRWUn1rYzKEOVnJknObsmFyiMUZqMz6yU4qDa_sEjVIVm_xRp5e2yoLgrhmEOYMCdT_7qLJpUUjtqE8s97qexne61NTsyIDa91FZZtB97wGEa_N09FXVHdvgyZN=w500-h500-s-no-gm?authuser=0",
    "Go Beyond": "https://lh3.googleusercontent.com/pw/AP1GczO6wkqmt_PjDcTTfTpWcH_t8Aet9Djkwn2zITW1pv3Fb4hOvy8LCiagpTYHqiLryUsgn_V-t6cLcQeWKGQG7R818NH10cm09RT1EO_IKV4ncmDC8F7rgpcdfszcqyfsYAyAZeUuKw5o7oh-T_xh7HK9=w321-h157-s-no-gm?authuser=0",
    "Gonars": "https://lh3.googleusercontent.com/pw/AP1GczPMJrt3i_jbgUt6weXDcXswPuzkJuYxNzlSgCxHGkgSx4N0B5P8iz2s1k9pFiDtoc0u96bAqcmG96AYMCeaJMnJ9BPFqElWDYgjNXgfJ-swxJJXklrT5I2XhsRsqpHe3nRIHuo24JvD9y1tcVQTH9M1=w869-h869-s-no-gm?authuser=0",
    "Kros Over 1": "https://lh3.googleusercontent.com/pw/AP1GczN2TOWKwTUGHd8i8bK-TdeKnmIsFI9Mvl-CHTxDTpBrux_lbX_hjQADvYinqxaEGHOlh-xXZ4-Qc4GpeWDJvTdlTO8gvtobtLtKx7Gw_nH2h6Ds0TAxv0zYidFVXQ5Ltxv5hZ_pyQSxjT1hK8nBeBuk=w214-h62-s-no-gm?authuser=0",
    "Kros Over 2": "https://lh3.googleusercontent.com/pw/AP1GczN2TOWKwTUGHd8i8bK-TdeKnmIsFI9Mvl-CHTxDTpBrux_lbX_hjQADvYinqxaEGHOlh-xXZ4-Qc4GpeWDJvTdlTO8gvtobtLtKx7Gw_nH2h6Ds0TAxv0zYidFVXQ5Ltxv5hZ_pyQSxjT1hK8nBeBuk=w214-h62-s-no-gm?authuser=0",
    "Kros Over 3": "https://lh3.googleusercontent.com/pw/AP1GczN2TOWKwTUGHd8i8bK-TdeKnmIsFI9Mvl-CHTxDTpBrux_lbX_hjQADvYinqxaEGHOlh-xXZ4-Qc4GpeWDJvTdlTO8gvtobtLtKx7Gw_nH2h6Ds0TAxv0zYidFVXQ5Ltxv5hZ_pyQSxjT1hK8nBeBuk=w214-h62-s-no-gm?authuser=0",
    "Tigers Goriziana": "https://lh3.googleusercontent.com/pw/AP1GczO5Dn5rZOSF9W_83Cht4XcWWxVyttYbnSQJMNtBsp7S_DdQp_6Wjpkz9q-Gsh1rgL85mGL2n6N716MZYh5GNKtVP9qQ8A8wefANtpQoQYEw5FIbc4BXllYEAk20msp-R8_88dxlVaC-1tVc8pdhQ3_7=w219-h230-s-no-gm?authuser=0",
    "Trieste All IN": "https://lh3.googleusercontent.com/pw/AP1GczO_DtsNkpA5q2gQuXnEUFSyJ5D2WgfClPttF4fPJIKPB0bHBjZjc83jYieA8tldsOeucFI_IQpplggi2iggOyL-I8laQpBloXB4yUb4gy5MCEULM7vJ6uyJEHqk6pouSy31TocqsregAuoQxTc2BXX0=w911-h869-s-no-gm?authuser=0",
    "UBC Baskin": "https://lh3.googleusercontent.com/pw/AP1GczN-z6k4dhAwPDBQgmDktTYzIjYssa2c92MEgGnWnga5qxeorjTCZmuB-O27uaFXHulH3oCiskVqkxbPleCp2WHh_P-7xXPZ8N4rWEnUOJ5kKpQYEjDVee6t2lvU-oSnhIwvoN1LXpSYG5r52iv-ZLHX=w275-h183-s-no-gm?authuser=0",
    "Zio Pino Kobe": "https://lh3.googleusercontent.com/pw/AP1GczMOZxJka2YIXL3vheahwitcrb7TL-IRwmdj2LpCwmCl0B7GCX6K_7ULOPWOBIaJm0AAnnjbjum5Q2S9skdZtIa-4YOdt16LvMP6WPeH7E3brPKiiMXrpyRbTolkm-7Xlpu1vjGm2lzQpZysyw8fAxlM=w579-h187-s-no-gm?authuser=0",
    "Zio Pino Magic": "https://lh3.googleusercontent.com/pw/AP1GczMOZxJka2YIXL3vheahwitcrb7TL-IRwmdj2LpCwmCl0B7GCX6K_7ULOPWOBIaJm0AAnnjbjum5Q2S9skdZtIa-4YOdt16LvMP6WPeH7E3brPKiiMXrpyRbTolkm-7Xlpu1vjGm2lzQpZysyw8fAxlM=w579-h187-s-no-gm?authuser=0",
    "Zio Pino Moki": "https://lh3.googleusercontent.com/pw/AP1GczMOZxJka2YIXL3vheahwitcrb7TL-IRwmdj2LpCwmCl0B7GCX6K_7ULOPWOBIaJm0AAnnjbjum5Q2S9skdZtIa-4YOdt16LvMP6WPeH7E3brPKiiMXrpyRbTolkm-7Xlpu1vjGm2lzQpZysyw8fAxlM=w579-h187-s-no-gm?authuser=0",
    "Zio Pio Cainero": "https://lh3.googleusercontent.com/pw/AP1GczMOZxJka2YIXL3vheahwitcrb7TL-IRwmdj2LpCwmCl0B7GCX6K_7ULOPWOBIaJm0AAnnjbjum5Q2S9skdZtIa-4YOdt16LvMP6WPeH7E3brPKiiMXrpyRbTolkm-7Xlpu1vjGm2lzQpZysyw8fAxlM=w579-h187-s-no-gm?authuser=0",
}

# Rosa Carpe Diem: (nome completo, ruolo, iscritto EISI, iscritto CSAIN)
ROSTER = [
    ("Vincenzo De Luca Bossa", 1, True, True),
    ("Arjen Kopic", 1, True, True),
    ("Ettore Chiandotto", 1, False, True),
    ("Giulia Bedin", 1, True, True),
    ("Elena Ciuffreda", 2, True, True),
    ("Alessandro Gallas", 2, True, True),
    ("Ezio Bonanno", 2, True, True),
    ("Emanuele Deola", 2, True, True),
    ("Giuseppe Virgulin", 2, True, True),
    ("Alice Agazzi", 2, True, True),
    ("Matteo Guerra", 2, False, True),
    ("Simone Botta", 3, True, True),
    ("Dominik Wayer", 3, True, True),
    ("Francesco Dose", 3, True, True),
    ("Gabriele Tell", 3, True, True),
    ("Gabriele Bortot", 3, True, True),
    ("Alexander Pian", 3, True, True),
    ("Christian Spotswood", 3, True, True),
    ("Lorenzo Macorin", 3, True, True),
    ("Gabriele Macorin", 3, True, True),
    ("Leon Chiandotto", 3, True, True),
    ("Alen Kopic", 4, True, True),
    ("Pietro Boscarol", 4, True, True),
    ("Gaia Miniussi", 4, True, True),
    ("Erik Franceschini", 4, True, True),
    ("Alessandro Lupieri", 4, True, True),
    ("Federico Rossi", 4, True, True),
    ("Oberdan Agazzi", 4, True, True),
    ("Giulia", 4, True, True),
    ("Francesco Pecol", 4, True, True),
    ("Elia Chiandotto", 4, False, True),
    ("Alessio Beltrame", 5, True, True),
    ("Francisco Mininel", 5, True, True),
    ("Andrea Cherubin", 5, True, True),
    ("Mattia Capraro", 5, True, True),
    ("Mario Ciuffreda", 5, True, True),
    ("Linda Zanolla", 5, True, True),
    ("Ilaria Revelant", 5, True, True),
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalars(select(Federation)).first():
            print("Database gia popolato, nessuna azione.")
            return

        eisi = Federation(
            code="EISI",
            name="Ente Italiano Sport Inclusivi",
            logo_url=f"{LOGO}/eisi.png",
            color="#5b6b7d",
        )
        csain = Federation(
            code="CSAIN",
            name="Baskin CSAIN",
            logo_url=f"{LOGO}/csain.png",
            color="#8e1b32",
        )
        db.add_all([eisi, csain])
        db.flush()

        ours = Team(
            name="CarpeDiem Baskin",
            logo_url=f"{LOGO}/carpediem.png",
            city="Fiumicello Villa Vicentina",
            is_ours=True,
            federations=[eisi, csain],
        )
        db.add(ours)
        db.flush()

        # Squadre dei due campionati (la Carpe Diem e associata a entrambi)
        teams = {OUR_TEAM: ours}
        for name in CSAIN_TEAMS:
            feds = [csain, eisi] if name in TEAMS_BOTH else [csain]
            team = Team(name=name, logo_url=TEAM_LOGOS.get(name), federations=feds)
            db.add(team)
            teams[name] = team
        for name in EISI_TEAMS:
            team = Team(name=name, logo_url=TEAM_LOGOS.get(name), federations=[eisi])
            db.add(team)
            teams[name] = team
        db.flush()

        # Palestre per citta (aggiornate con info precise)
        venue_data = {
            "Udine": ("Palestra Bearzi - Zio Pino", "https://maps.google.com/?q=Palestra+Bearzi+Udine"),
            "Muggia": ("Palestra Muggia", "https://maps.google.com/?q=Palestra+Muggia"),
            "Turriaco": ("Palestra Turriaco", "https://maps.google.com/?q=Palestra+Turriaco"),
            "Trieste": ("Palestra Trieste", "https://maps.google.com/?q=Palestra+Trieste"),
            "Monfalcone": ("Palestra Monfalcone", "https://maps.google.com/?q=Palestra+Monfalcone"),
            "Latisana": ("Palestra Latisana", "https://maps.google.com/?q=Palestra+Latisana"),
            "Cividale": ("Cividale", "https://maps.google.com/?q=Cividale"),
            "Gorizia": ("Gorizia", "https://maps.google.com/?q=Gorizia"),
            "Pordenone - PalaMarson": ("Pordenone - PalaMarson", "https://maps.google.com/?q=PalaMarson+Pasiano"),
            "Pala Macoratti -Gradisca-": ("Pala Macoratti -Gradisca-", "https://maps.google.com/?q=Pala+Macoratti+Gradisca"),
        }
        # Per CSAIN e EISI, raccogliamo tutte le città dai due calendari
        cities = {m[2] for m in CSAIN_MATCHES} | {m[2] for m in EISI_MATCHES}
        venues = {}
        for city in sorted(cities):
            name, url = venue_data.get(city, (f"Palestra {city}", f"https://maps.google.com/?q=Palestra+{city}"))
            venue = Venue(name=name, address=None, maps_url=url)
            venues[city] = venue
            db.add(venue)
        db.flush()

        # Rosa Carpe Diem (l'eventuale sottotipo del ruolo 2 si imposta dall'area staff)
        for full_name, role, in_eisi, in_csain in ROSTER:
            parts = full_name.split(" ", 1)
            feds = []
            if in_eisi:
                feds.append(eisi)
            if in_csain:
                feds.append(csain)
            db.add(
                Player(
                    first_name=parts[0],
                    last_name=parts[1] if len(parts) > 1 else "",
                    role=role,
                    active=True,
                    federations=feds,
                )
            )
        db.flush()

        for date_str, match_time, city, code, home_name, away_name in CSAIN_MATCHES:
            d = date.fromisoformat(date_str)
            db.add(
                Match(
                    match_date=d,
                    match_time=match_time,
                    federation_id=csain.id,
                    home_team_id=teams[home_name].id,
                    away_team_id=teams[away_name].id,
                    venue_id=venues[city].id,
                    competition="Campionato CSAIN 2026/2027",
                    matchday=int(code[1:]),
                    published=True,
                )
            )

        EVENT_MATCHES = [
    ("2026-12-05", time(14, 30), "Palestra Turriaco", "EV01", OUR_TEAM, "Zio Pino Kobe"),
    ("2026-12-06", time(10, 0), "Palestra Turriaco", "EV02", OUR_TEAM, "Bazinga"),
]

# Calendario EISI
        for date_str, match_time, city, code, home_name, away_name in EISI_MATCHES:
            d = date.fromisoformat(date_str)
            db.add(
                Match(
                    match_date=d,
                    match_time=match_time,
                    federation_id=eisi.id,
                    home_team_id=teams[home_name].id,
                    away_team_id=teams[away_name].id,
                    venue_id=venues[city].id,
                    competition="Campionato EISI 2026/2027",
                    matchday=int(code[1:]),
                    published=True,
                )
            )

        # Eventi speciali
        for date_str, match_time, city, code, home_name, away_name in EVENT_MATCHES:
            d = date.fromisoformat(date_str)
            db.add(
                Match(
                    match_date=d,
                    match_time=match_time,
                    federation_id=csain.id,
                    home_team_id=teams[home_name].id,
                    away_team_id=teams[away_name].id,
                    venue_id=venues[city].id,
                    competition="Torneo Gemelli Diversi",
                    matchday=int(code[-2:] if len(code) >= 2 else code),
                    published=True,
                )
            )

        db.commit()
        print(
            f"Database popolato: {len(CSAIN_MATCHES)} gare CSAIN, {len(EISI_MATCHES)} gare EISI e {len(ROSTER)} giocatori."
        )
    finally:
        db.close()


if __name__ == "__main__":
    if "reset" in sys.argv[1:]:
        Base.metadata.drop_all(bind=engine)
        print("Tabelle svuotate.")
    seed()
