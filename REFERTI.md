# Referti & statistiche (area staff)

Modulo riservato allo staff per gestire referti gara, statistiche di squadra e
statistiche individuali delle stagioni 2026/2027 di CSAIN ed EISI.

La pagina è **separata dall'app pubblica**: si apre su `/referti`, non è
collegata al calendario pubblico e non viene pubblicata su GitHub Pages.
All'apertura mostra solo il modulo di accesso con password staff
(`STAFF_PASSWORD`); nessun dato viene incluso nell'HTML della pagina.
Quando la sessione staff è attiva compare la voce **Referti** nella barra di
navigazione dell'app (e un riquadro in **Gestione**) che apre questa pagina.

Tutti i dati passano da `/api/admin/...` e richiedono la sessione staff, quindi
anche chi conoscesse l'indirizzo della pagina senza password non può leggere
referti o statistiche.

## Dati

Il modulo **non duplica** gare, giocatori e convocazioni: riusa le entità del
calendario (`Match`, `Player`, `Convocation`) e aggiunge solo:

- `Player.jersey_number` — numero di maglia (opzionale, usato nei referti);
- `MatchReport` — testata del referto (stato `draft`/`final`, note, totali);
- `MatchReportLine` — riga per giocatore con punti per quarto e statistiche
  avanzate opzionali.

Le statistiche usano per impostazione predefinita **solo i referti
definitivi**; le gare senza referto restano visibili ma non entrano nei totali.

## Flusso consigliato

1. **Sincronizza il calendario** da *Partite & referti → Importa dal
   calendario*: scarica gare, convocazioni e anagrafiche dall'API pubblica.
   Il sync non tocca mai i referti e non sovrascrive il punteggio di una gara
   con referto definitivo (il calendario pubblico può avere punteggi invertiti).
2. **Compila il referto** aprendo una gara: numero di maglia, punti per quarto
   per i giocatori CarpeDiem e per gli avversari. Il tabellone in alto calcola
   in tempo reale parziali, progressivo e risultato finale.
3. **Salva come definitivo**: il referto entra nelle statistiche e, se
   richiesto, il punteggio viene riportato sulla gara del calendario.
4. **Consulta le statistiche** in *Dashboard* (andamento, parziali, migliori
   marcatori, split casa/trasferta e per federazione), *Giocatori* (filtri per
   stagione, federazione, avversario; massimo stagionale e contro chi) e
   *Avversari* (bilancio contro ogni squadra).

## Import da Excel

Il pulsante *Importa Excel* accetta il modello di referto usato dallo staff
(es. `15nov26.xlsx`): due blocchi squadra affiancati, numeri di maglia, punti
per quarto. L'import:

- riconosce i quarti e calcola i totali, segnalando eventuali incoerenze;
- propone l'abbinamento dei giocatori per nome/numero e lascia risolvere a mano
  i casi ambigui (es. due giocatori con lo stesso cognome);
- permette di invertire casa/trasferta e scegliere il foglio del workbook;
- mostra un'anteprima modificabile prima di applicare i dati al referto.

## Endpoint principali

| Metodo | Percorso | Uso |
| --- | --- | --- |
| GET | `/api/admin/reports/board` | Elenco gare e stato referti |
| GET | `/api/admin/reports/stats` | Statistiche squadra, giocatori, avversari |
| GET | `/api/admin/reports/players/{id}` | Dettaglio giocatore |
| GET | `/api/admin/reports/{match_id}` | Referto di una gara |
| PUT | `/api/admin/reports/{match_id}` | Salva bozza o definitivo |
| DELETE | `/api/admin/reports/{match_id}` | Elimina referto |
| POST | `/api/admin/reports/parse-excel` | Anteprima import Excel |
| POST | `/api/admin/sync-public` | Allinea dal calendario pubblico |

## Note tecniche

- L'import Excel richiede `openpyxl` (già in `requirements.txt`).
- Gli asset del modulo sono `static/css/reports.css`, `static/js/reports.js` e
  `static/js/referti.js`, caricati solo dalla pagina `/referti` (non dalla
  pagina pubblica e non precaricati dal service worker).
- La pagina `/referti` invia `X-Robots-Tag: noindex, nofollow` ed è esclusa
  dalla generazione del sito pubblico (`calendar_site/generate.py`).
- La sincronizzazione pubblica è idempotente e ignora eventuali convocati
  duplicati restituiti dall'API, segnalandoli nei `warnings`.
