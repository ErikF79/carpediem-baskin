"""Lettura dei referti Excel (formato usato dallo staff CarpeDiem).

Il file di riferimento contiene, per ogni foglio, due blocchi squadra:
- colonna A: nome/cognome del giocatore
- colonna B: numero di maglia
- colonne successive: punti segnati, raggruppati per quarto (1Q, 2Q, 3Q, 4Q)
- una colonna finale con il totale (formula SUM)

I quarti sono individuati dalle intestazioni "1Q".."4Q" e dalle celle unite.
La colonna totale viene riconosciuta dalle formule =SUM(...) presenti nelle
righe dei giocatori. In questo modo funzionano sia il foglio CSAIN sia EISI.
"""
from __future__ import annotations

import io
import re
import unicodedata
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

QUARTER_RE = re.compile(r"^\s*([1-4])\s*Q\s*$", re.IGNORECASE)
TOTAL_WORDS = {"totale", "total", "tot", "somma"}


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9 ]+", " ", value.lower())
    return " ".join(value.split())


def _to_int(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(round(value))
    text = str(value).strip().replace(",", ".")
    if not text:
        return 0
    try:
        return int(round(float(text)))
    except ValueError:
        return 0


def _numeric(value: Any) -> bool:
    if value is None or value == "" or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    try:
        float(str(value).replace(",", "."))
        return True
    except ValueError:
        return False


def _merged_range(ws, cell):
    for merged in ws.merged_cells.ranges:
        if cell.coordinate in merged:
            return merged
    return None


def _match_player(
    name: str, number: int | None, players: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, str, list[dict[str, Any]]]:
    """Abbina il nome scritto nel referto a un giocatore della rosa.

    Restituisce (giocatore, confidenza, candidati). La confidenza e' "high",
    "medium", "low" oppure "none"; i candidati servono alla UI per risolvere
    eventuali casi ambigui (es. due fratelli con lo stesso cognome).
    """
    normalized = _norm(name)
    if not normalized:
        return None, "none", []

    scored: list[tuple[int, dict[str, Any]]] = []
    for player in players:
        full = _norm(f"{player.get('first_name', '')} {player.get('last_name', '')}")
        first = _norm(player.get("first_name", ""))
        last = _norm(player.get("last_name", ""))
        score = 0
        if number is not None and player.get("jersey_number") == number:
            score += 40
        if normalized == full:
            score += 120
        elif normalized == last:
            score += 70
        elif normalized == first:
            score += 25
        elif normalized in full:
            score += 55
        elif last and (last.startswith(normalized) or normalized.startswith(last)):
            score += 45
        elif set(normalized.split()) <= set(full.split()):
            score += 40
        else:
            # ultimo tentativo: singole parti del nome (es. "de luca" -> "de luca bossa")
            parts = normalized.split()
            if len(parts) > 1 and all(part in full for part in parts):
                score += 35
        if score:
            scored.append((score, player))

    if not scored:
        return None, "none", []

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_player = scored[0]
    candidates = [
        {
            "player_id": p["id"],
            "name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip(),
            "role": p.get("role"),
            "jersey_number": p.get("jersey_number"),
            "score": s,
        }
        for s, p in scored[:5]
    ]
    # Pari merito: non scegliamo a caso, lasciamo decidere allo staff.
    if len(scored) > 1 and scored[1][0] == best_score:
        confidence = "low"
    elif best_score >= 70:
        confidence = "high"
    elif best_score >= 40:
        confidence = "medium"
    else:
        confidence = "low"
    return best_player, confidence, candidates


def _parse_block(
    values_ws,
    formula_ws,
    header_row: int,
    quarter_cells: dict[int, Any],
    players: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Legge un blocco squadra a partire dalla riga di intestazione dei quarti."""
    quarter_ranges: dict[int, tuple[int, int]] = {}
    for quarter, cell in quarter_cells.items():
        merged = _merged_range(values_ws, cell)
        if merged:
            quarter_ranges[quarter] = (merged.min_col, merged.max_col)
        else:
            quarter_ranges[quarter] = (cell.column, cell.column)

    first_quarter_col = min(r[0] for r in quarter_ranges.values())

    # Righe giocatore: nomi in colonna A, fino alla riga totale o a una riga vuota.
    data_rows: list[int] = []
    for row in range(header_row + 1, min(header_row + 60, values_ws.max_row + 1)):
        name_value = values_ws.cell(row=row, column=1).value
        if isinstance(name_value, str) and QUARTER_RE.match(name_value):
            break
        if name_value is None or str(name_value).strip() == "":
            if data_rows:
                break
            continue
        if _norm(name_value) in TOTAL_WORDS:
            break
        data_rows.append(row)

    if not data_rows:
        return None

    # La colonna totale e' quella che contiene piu' formule =SUM(...) nelle righe.
    total_col_votes: dict[int, int] = {}
    for row in data_rows:
        for col in range(first_quarter_col, values_ws.max_column + 1):
            formula = formula_ws.cell(row=row, column=col).value
            if isinstance(formula, str) and formula.strip().upper().startswith("=SUM"):
                total_col_votes[col] = total_col_votes.get(col, 0) + 1
    total_col = max(total_col_votes, key=total_col_votes.get) if total_col_votes else None

    lines: list[dict[str, Any]] = []
    for row in data_rows:
        name = str(values_ws.cell(row=row, column=1).value).strip()
        number_raw = values_ws.cell(row=row, column=2).value
        number = _to_int(number_raw) if _numeric(number_raw) else None
        quarters = [0, 0, 0, 0]
        for quarter, (min_col, max_col) in quarter_ranges.items():
            if total_col is not None and min_col >= total_col:
                continue
            end_col = max_col
            if total_col is not None:
                end_col = min(end_col, total_col - 1)
            if end_col < min_col:
                continue
            total = 0
            for col in range(min_col, end_col + 1):
                total += _to_int(values_ws.cell(row=row, column=col).value)
            quarters[quarter - 1] = total

        player, confidence, candidates = _match_player(name, number, players)
        lines.append(
            {
                "name": name,
                "jersey_number": number,
                "q1": quarters[0],
                "q2": quarters[1],
                "q3": quarters[2],
                "q4": quarters[3],
                "total": sum(quarters),
                "player_id": player["id"] if confidence in ("high", "medium") else None,
                "matched_name": (
                    f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
                    if player
                    else None
                ),
                "confidence": confidence,
                "candidates": candidates,
            }
        )

    totals = [sum(line[f"q{i}"] for line in lines) for i in range(1, 5)]
    return {
        "header_row": header_row,
        "lines": lines,
        "totals": totals,
        "total": sum(totals),
        "total_column": get_column_letter(total_col) if total_col else None,
    }


def _sheet_side_score(sheet_name: str, opponent_name: str, federation_code: str) -> int:
    sheet = _norm(sheet_name)
    score = 0
    if federation_code and _norm(federation_code) in sheet:
        score += 3
    for token in _norm(opponent_name).split():
        if len(token) < 3:
            continue
        if token in sheet or (len(token) > 4 and token[:4] in sheet):
            score += 2
    return score


def parse_workbook(
    content: bytes,
    players: list[dict[str, Any]],
    opponent_name: str = "",
    federation_code: str = "",
) -> dict[str, Any]:
    """Estrae tutti i fogli e i blocchi squadra dal file Excel."""
    values_wb = load_workbook(io.BytesIO(content), data_only=True)
    formula_wb = load_workbook(io.BytesIO(content), data_only=False)
    sheets: list[dict[str, Any]] = []
    warnings: list[str] = []

    for values_ws in values_wb.worksheets:
        formula_ws = formula_wb[values_ws.title]
        headers: dict[int, dict[int, Any]] = {}
        for row in values_ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    match = QUARTER_RE.match(cell.value)
                    if match:
                        headers.setdefault(cell.row, {})[int(match.group(1))] = cell

        blocks: list[dict[str, Any]] = []
        for header_row in sorted(headers):
            quarter_cells = headers[header_row]
            if len(quarter_cells) < 2:
                continue
            # Ignora i riepiloghi/scoreboard: le intestazioni dei quarti del
            # blocco squadra partono dalle prime colonne (C o giu' di li).
            if min(cell.column for cell in quarter_cells.values()) > 6:
                continue
            block = _parse_block(
                values_ws, formula_ws, header_row, quarter_cells, players
            )
            if block and block["lines"]:
                blocks.append(block)

        sheet_warnings: list[str] = []
        if not blocks:
            sheet_warnings.append(
                "Nessun blocco giocatori riconosciuto: il foglio sembra vuoto o in un formato diverso."
            )

        # Il blocco "nostro" e' quello con piu' nomi riconosciuti nella rosa.
        match_counts = [
            sum(1 for line in block["lines"] if line["confidence"] != "none")
            for block in blocks
        ]
        ours_index: int | None = None
        if blocks:
            best = max(range(len(blocks)), key=lambda i: match_counts[i])
            if match_counts[best] > 0:
                ours_index = best
            elif len(blocks) == 2:
                # Senza riscontri la scelta resta allo staff; proponiamo il secondo
                # blocco perche' nel file storico CarpeDiem e' quasi sempre in basso.
                ours_index = 1
                sheet_warnings.append(
                    "Non ho riconosciuto i giocatori CarpeDiem: controlla quale blocco è il nostro."
                )

        opponent_index = None
        if len(blocks) == 2 and ours_index is not None:
            opponent_index = 1 - ours_index

        suggested = _sheet_side_score(values_ws.title, opponent_name, federation_code)
        sheets.append(
            {
                "name": values_ws.title,
                "blocks": blocks,
                "ours_index": ours_index,
                "opponent_index": opponent_index,
                "match_counts": match_counts,
                "suggestion_score": suggested,
                "warnings": sheet_warnings,
            }
        )

    if not sheets:
        warnings.append("Il file non contiene fogli leggibili.")

    suggested_sheet = None
    if sheets:
        best = max(range(len(sheets)), key=lambda i: sheets[i]["suggestion_score"])
        if sheets[best]["suggestion_score"] > 0:
            suggested_sheet = best
        elif len(sheets) == 1:
            suggested_sheet = 0

    return {
        "sheets": sheets,
        "suggested_sheet": suggested_sheet,
        "warnings": warnings,
    }
