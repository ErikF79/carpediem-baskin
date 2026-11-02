# CarpeDiem Baskin — pagina pubblica

La cartella `docs/` è pubblicata da GitHub Pages su
<https://erikf79.github.io/carpediem-baskin/>.

## Come funziona

La pagina è una copia dell'app (stesso layout e stesse funzioni) ma:

- **CSS, JS e immagini sono copiati qui dentro** (`docs/static/`), quindi la
  pagina si apre e si veste correttamente anche se il backend è spento;
- **`docs/data.json`** contiene l'ultimo snapshot dei dati (gare, giocatori,
  dettagli delle gare con convocazioni/indisponibili/passaggi). Viene mostrato
  subito, così le informazioni ci sono sempre;
- appena il backend risponde, l'API aggiorna i dati in tempo reale; se non
  risponde resta visibile lo snapshot con la data di aggiornamento nel footer.

L'area staff non è presente nella pagina pubblica: usa l'app
(<https://carpediem-baskin.onrender.com>).

## Aggiornare la pagina pubblica

Dopo modifiche a template, CSS, JS o per rinfrescare lo snapshot:

```bash
.\.venv\Scripts\python.exe calendar_site\generate.py
git add docs
git commit -m "Aggiorna pagina pubblica"
git push
```

Se il backend è spento lo script mantiene lo snapshot precedente e aggiorna
comunque HTML e risorse.

## Album fotografici

Gli album si dichiarano nel file `albums.json` nella radice del progetto
(vedi `albums.example.json`). Vengono inclusi nello snapshot e mostrati nella
scheda "Album" della pagina pubblica.
