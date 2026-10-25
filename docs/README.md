# Calendario Carpe Diem

Pagina statica generata dal DB dell'app (`carpediem.db`).

## Come pubblicare il link pubblico

### Opzione 1: GitHub Pages (consigliata)
1. Crea un nuovo repository su GitHub (es. `calendario-carpe-diem`)
2. Carica solo il file `index.html`
3. Vai su `Settings` → `Pages`
4. Seleziona `Deploy from a branch` → `main` / `root`
5. Salva: il link sarà `https://tuonome.github.io/calendario-carpe-diem`

### Opzione 2: Netlify (instant)
1. Vai su [netlify.com/drop](https://netlify.com/drop)
2. Trascina `index.html` nella pagina
3. Ottieni subito un link pubblico (es. `https://calendario-carpe-123.netlify.app`)

## Come aggiornare i dati

Quando il DB cambia, rigenera la pagina:

```bash
python calendar_site/generate.py
```

Poi ricarica `index.html` nel repository (o su Netlify).
