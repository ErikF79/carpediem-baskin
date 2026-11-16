"""Importazione idempotente dal calendario pubblico CarpeDiem.

Il sito https://erikf79.github.io/carpediem-baskin/ usa le API pubbliche di
questo stesso progetto. Questa funzione permette di allineare una copia locale
del database (o un'installazione separata) a quelle API: squadre, giocatori,
palestre, gare e convocazioni. I referti non vengono mai toccati.
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.error
import urllib.request
from datetime import date, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import (
    Convocation,
    Federation,
    Match,
    Player,
    Team,
    Venue,
)


def _norm(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9 ]+", " ", value.lower())
    return " ".join(value.split())


def _fetch_json(url: str, timeout: int = 30) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "CarpeDiemCalendar/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    text = str(value)
    if len(text) >= 5:
        try:
            return time(int(text[:2]), int(text[3:5]))
        except ValueError:
            return None
    return None


def _federation_map(db: Session, public_config: dict) -> dict[str, Federation]:
    result: dict[str, Federation] = {}
    for federation in db.scalars(select(Federation)).all():
        result[federation.code.upper()] = federation
    for data in public_config.get("federations", []) or []:
        code = (data.get("code") or "").strip().upper()
        if not code:
            continue
        federation = result.get(code)
        if not federation:
            federation = Federation(
                code=code,
                name=data.get("name") or code,
                logo_url=data.get("logo_url"),
                color=data.get("color"),
            )
            db.add(federation)
            db.flush()
        else:
            if data.get("name"):
                federation.name = data["name"]
            if data.get("logo_url"):
                federation.logo_url = data["logo_url"]
            if data.get("color"):
                federation.color = data["color"]
        result[code] = federation
    return result


def _team_federations(
    db: Session, codes: list[str], federations: dict[str, Federation]
) -> list[Federation]:
    rows: list[Federation] = []
    for code in codes:
        federation = federations.get((code or "").upper())
        if federation:
            rows.append(federation)
    return rows


def _sync_team(
    db: Session,
    data: dict,
    teams_by_name: dict[str, Team],
    federations: dict[str, Federation],
    counters: dict[str, int],
) -> Team:
    name = (data.get("name") or "").strip()
    key = _norm(name)
    team = teams_by_name.get(key)
    if not team:
        team = Team(name=name)
        db.add(team)
        teams_by_name[key] = team
        counters["teams_created"] += 1
    else:
        counters["teams_updated"] += 1
    team.name = name or team.name
    if data.get("logo_url"):
        team.logo_url = data["logo_url"]
    if data.get("city"):
        team.city = data["city"]
    team.is_ours = bool(data.get("is_ours"))
    codes = [f.get("code", "") for f in (data.get("federations") or [])]
    target = _team_federations(db, codes, federations)
    if target:
        team.federations = target
    return team


def _sync_player(
    db: Session,
    data: dict,
    players_by_code: dict[str, Player],
    players_by_name: dict[str, Player],
    federations: dict[str, Federation],
    counters: dict[str, int],
) -> Player:
    code_eisi = (data.get("code_eisi") or "").strip()
    code_csain = (data.get("code_csain") or "").strip()
    full_name = _norm(f"{data.get('first_name', '')} {data.get('last_name', '')}")
    # Il nome completo e' piu' affidabile dei codici: nel calendario pubblico
    # esistono codici EISI duplicati per errore (es. Bedin/Cherubin).
    player = players_by_name.get(full_name)
    if not player:
        for code in (code_eisi, code_csain):
            if code and code in players_by_code:
                player = players_by_code[code]
                break

    created = False
    if not player:
        player = Player(
            first_name=data.get("first_name") or "",
            last_name=data.get("last_name") or "",
            role=int(data.get("role") or 1),
        )
        db.add(player)
        created = True
        counters["players_created"] += 1
        players_by_name[full_name] = player
    else:
        counters["players_updated"] += 1

    player.first_name = data.get("first_name") or player.first_name
    player.last_name = data.get("last_name") or player.last_name
    player.role = int(data.get("role") or player.role or 1)
    player.role2_type = data.get("role2_type")
    if data.get("jersey_number") is not None:
        player.jersey_number = data.get("jersey_number")
    player.shot_distance_cm = data.get("shot_distance_cm")
    player.photo_url = data.get("photo_url")
    player.code_eisi = code_eisi or None
    player.code_csain = code_csain or None
    player.active = bool(data.get("active", True))
    player.email = data.get("email")
    player.phone = data.get("phone")

    if code_eisi:
        players_by_code[code_eisi] = player
    if code_csain:
        players_by_code[code_csain] = player
    players_by_name[full_name] = player

    codes = [f.get("code", "") for f in (data.get("federations") or [])]
    target = _team_federations(db, codes, federations)
    if target:
        if created or not player.federations:
            player.federations = target
        else:
            existing = {f.id for f in player.federations}
            for federation in target:
                if federation.id not in existing:
                    player.federations.append(federation)
    return player


def _sync_venue(
    db: Session,
    data: dict | None,
    venues_by_name: dict[str, Venue],
    counters: dict[str, int],
) -> Venue | None:
    if not data:
        return None
    name = (data.get("name") or "").strip()
    if not name:
        return None
    key = _norm(name)
    venue = venues_by_name.get(key)
    if not venue:
        venue = Venue(name=name)
        db.add(venue)
        venues_by_name[key] = venue
        counters["venues_created"] += 1
    else:
        counters["venues_updated"] += 1
    venue.name = name
    if data.get("address"):
        venue.address = data["address"]
    if data.get("maps_url"):
        venue.maps_url = data["maps_url"]
    return venue


def sync_from_public(db: Session, base_url: str | None = None) -> dict:
    base = (base_url or settings.public_api_base or "").strip().rstrip("/")
    if not base:
        raise ValueError("Nessun calendario pubblico configurato")

    try:
        public_config = _fetch_json(f"{base}/api/config")
        public_players = _fetch_json(f"{base}/api/players?active_only=false")
        public_matches = _fetch_json(f"{base}/api/matches?include_unpublished=true")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Calendario pubblico non raggiungibile: {exc}") from exc

    counters = {
        "teams_created": 0,
        "teams_updated": 0,
        "players_created": 0,
        "players_updated": 0,
        "venues_created": 0,
        "venues_updated": 0,
        "matches_created": 0,
        "matches_updated": 0,
        "convocations_synced": 0,
    }
    warnings: list[str] = []

    federations = _federation_map(db, public_config)

    teams_by_name = {_norm(t.name): t for t in db.scalars(select(Team)).all()}
    venues_by_name = {_norm(v.name): v for v in db.scalars(select(Venue)).all()}
    players_by_name: dict[str, Player] = {}
    players_by_code: dict[str, Player] = {}
    for player in db.scalars(select(Player)).all():
        players_by_name[_norm(f"{player.first_name} {player.last_name}")] = player
        if player.code_eisi:
            players_by_code[player.code_eisi] = player
        if player.code_csain:
            players_by_code[player.code_csain] = player

    # Squadre (prima le squadre, servono alle gare)
    all_teams: dict[str, dict] = {}
    for match in public_matches:
        for side in ("home_team", "away_team"):
            if match.get(side):
                all_teams[_norm(match[side].get("name"))] = match[side]
    our_team_data = public_config.get("our_team")
    if our_team_data:
        all_teams[_norm(our_team_data.get("name"))] = our_team_data
    for data in all_teams.values():
        _sync_team(db, data, teams_by_name, federations, counters)
    db.flush()

    # Giocatori
    public_player_map: dict[int, Player] = {}
    for data in public_players:
        player = _sync_player(
            db, data, players_by_code, players_by_name, federations, counters
        )
        public_player_map[int(data.get("id"))] = player
    db.flush()

    # Gare
    matches_by_key: dict[tuple, Match] = {}
    for match in db.scalars(select(Match)).all():
        matches_by_key[
            (
                match.match_date,
                match.federation_id,
                match.home_team_id,
                match.away_team_id,
            )
        ] = match

    for data in public_matches:
        federation_code = ((data.get("federation") or {}).get("code") or "").upper()
        federation = federations.get(federation_code)
        home_data = data.get("home_team") or {}
        away_data = data.get("away_team") or {}
        home = teams_by_name.get(_norm(home_data.get("name")))
        away = teams_by_name.get(_norm(away_data.get("name")))
        if not federation or not home or not away:
            warnings.append(
                f"Gara {data.get('match_date')} saltata: federazione o squadre non riconosciute."
            )
            continue
        try:
            match_date = date.fromisoformat(str(data.get("match_date"))[:10])
        except ValueError:
            warnings.append(f"Gara con data non valida: {data.get('match_date')}")
            continue
        key = (match_date, federation.id, home.id, away.id)
        match = matches_by_key.get(key)
        if not match:
            match = Match(
                match_date=match_date,
                federation_id=federation.id,
                home_team_id=home.id,
                away_team_id=away.id,
            )
            db.add(match)
            matches_by_key[key] = match
            counters["matches_created"] += 1
        else:
            counters["matches_updated"] += 1
        match.match_time = _parse_time(data.get("match_time"))
        match.competition = data.get("competition")
        match.matchday = data.get("matchday")
        match.notes = data.get("notes")
        match.published = bool(data.get("published", True))
        # Un referto finale e' la fonte piu' affidabile: il calendario pubblico
        # puo' avere punteggi invertiti o non aggiornati, quindi non va
        # sovrascritto dal sync.
        final_report = (
            match.report is not None and match.report.status == "final"
        )
        if not final_report:
            if data.get("home_score") is not None:
                match.home_score = data.get("home_score")
            if data.get("away_score") is not None:
                match.away_score = data.get("away_score")
        venue = _sync_venue(db, data.get("venue"), venues_by_name, counters)
        if venue:
            match.venue = venue
    db.flush()

    # Convocazioni: solo per le gare che le hanno nel calendario pubblico.
    for data in public_matches:
        if not data.get("has_convocations"):
            continue
        federation_code = ((data.get("federation") or {}).get("code") or "").upper()
        federation = federations.get(federation_code)
        home = teams_by_name.get(_norm((data.get("home_team") or {}).get("name")))
        away = teams_by_name.get(_norm((data.get("away_team") or {}).get("name")))
        if not federation or not home or not away:
            continue
        try:
            match_date = date.fromisoformat(str(data.get("match_date"))[:10])
        except ValueError:
            continue
        match = matches_by_key.get((match_date, federation.id, home.id, away.id))
        if not match:
            continue
        try:
            detail = _fetch_json(f"{base}/api/matches/{data.get('id')}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            warnings.append(
                f"Convocazioni non importate per {data.get('match_date')}: {exc}"
            )
            continue
        items = detail.get("convocations") or []
        if not items:
            continue
        for old in list(match.convocations):
            db.delete(old)
        db.flush()
        seen_players: set[int] = set()
        for item in items:
            public_player_id = item.get("player_id")
            player = public_player_map.get(int(public_player_id)) if public_player_id else None
            if not player:
                public_player = item.get("player") or {}
                full = _norm(
                    f"{public_player.get('first_name', '')} {public_player.get('last_name', '')}"
                )
                player = players_by_name.get(full)
            if not player:
                warnings.append(
                    f"Convocato non riconosciuto: {item.get('player_id')} ({data.get('match_date')})"
                )
                continue
            if player.id in seen_players:
                warnings.append(
                    f"Convocato duplicato ignorato: {player.first_name} {player.last_name} "
                    f"({data.get('match_date')})"
                )
                continue
            seen_players.add(player.id)
            db.add(
                Convocation(
                    match_id=match.id,
                    player_id=player.id,
                    kind=item.get("kind") or "starter",
                    slot_order=item.get("slot_order"),
                )
            )
            counters["convocations_synced"] += 1

    db.commit()
    return {
        "base_url": base,
        "counters": counters,
        "warnings": warnings,
    }
