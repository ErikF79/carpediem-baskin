"""Referti gara e statistiche della stagione.

Tutti gli endpoint sono riservati allo staff. Il modulo riusa le gare, i
giocatori e le convocazioni gia' presenti nel calendario: non duplica dati.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..database import get_db
from ..models import (
    Convocation,
    Federation,
    Match,
    MatchReport,
    MatchReportLine,
    Player,
    Setting,
    Team,
    Venue,
)
from ..public_sync import sync_from_public
from ..reports_excel import parse_workbook
from ..seasons import current_season_label, season_range
from ..security import require_staff

router = APIRouter(
    prefix="/api/admin",
    tags=["reports"],
    dependencies=[Depends(require_staff)],
)

QUARTERS = ("q1", "q2", "q3", "q4")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _match_options():
    return (
        selectinload(Match.federation),
        selectinload(Match.home_team).selectinload(Team.federations),
        selectinload(Match.away_team).selectinload(Team.federations),
        selectinload(Match.venue),
        selectinload(Match.convocations).selectinload(Convocation.player),
        selectinload(Match.report)
        .selectinload(MatchReport.lines)
        .selectinload(MatchReportLine.player),
    )


def _load_match(db: Session, match_id: int) -> Match | None:
    return db.scalars(
        select(Match).where(Match.id == match_id).options(*_match_options())
    ).first()


def _our_team(db: Session) -> Team | None:
    return db.scalars(select(Team).where(Team.is_ours.is_(True))).first()


def _season_label(db: Session, requested: str | None) -> str:
    setting = db.get(Setting, "season_label")
    label = (requested or (setting.value if setting else None) or current_season_label()).strip()
    return label


def _team_brief(team: Team | None) -> dict | None:
    if not team:
        return None
    return {
        "id": team.id,
        "name": team.name,
        "logo_url": team.logo_url,
        "city": team.city,
        "is_ours": team.is_ours,
    }


def _player_brief(player: Player | None) -> dict | None:
    if not player:
        return None
    return {
        "id": player.id,
        "first_name": player.first_name,
        "last_name": player.last_name,
        "name": f"{player.first_name} {player.last_name}".strip(),
        "photo_url": player.photo_url,
        "role": player.role,
        "role2_type": player.role2_type,
        "jersey_number": player.jersey_number,
        "code_eisi": player.code_eisi,
        "code_csain": player.code_csain,
        "active": player.active,
    }


def _line_out(line: MatchReportLine) -> dict:
    player = line.player
    name = (
        f"{player.first_name} {player.last_name}".strip()
        if player
        else (line.player_name or "")
    )
    return {
        "id": line.id,
        "team_side": line.team_side,
        "player_id": line.player_id,
        "player": _player_brief(player),
        "player_name": line.player_name,
        "name": name,
        "jersey_number": line.jersey_number
        if line.jersey_number is not None
        else (player.jersey_number if player else None),
        "played": line.played,
        "q1": line.q1,
        "q2": line.q2,
        "q3": line.q3,
        "q4": line.q4,
        "total": line.total,
        "fouls": line.fouls,
        "rebounds": line.rebounds,
        "assists": line.assists,
        "steals": line.steals,
        "turnovers": line.turnovers,
        "blocks": line.blocks,
        "minutes": line.minutes,
        "notes": line.notes,
        "sort_order": line.sort_order,
    }


def _report_totals(report: MatchReport | None) -> tuple[list[int], list[int]]:
    ours = [0, 0, 0, 0]
    opponent = [0, 0, 0, 0]
    if report:
        for line in report.lines:
            target = ours if line.team_side == "ours" else opponent
            target[0] += line.q1 or 0
            target[1] += line.q2 or 0
            target[2] += line.q3 or 0
            target[3] += line.q4 or 0
    return ours, opponent


def _progressive(quarters: list[int]) -> list[int]:
    total = 0
    result: list[int] = []
    for value in quarters:
        total += value
        result.append(total)
    return result


def _result(our_score: int, opp_score: int) -> str:
    if our_score > opp_score:
        return "W"
    if our_score < opp_score:
        return "L"
    return "D"


def _match_summary(match: Match, our_team: Team | None) -> dict:
    home_ours = bool(match.home_team and match.home_team.is_ours)
    if not match.home_team.is_ours and match.away_team.is_ours:
        home_ours = False
    opponent = match.away_team if home_ours else match.home_team
    report = match.report
    ours_q, opp_q = _report_totals(report)
    has_report = report is not None
    use_report = has_report and (bool(report.lines) or report.status == "final")

    if use_report:
        our_score = sum(ours_q)
        opp_score = sum(opp_q)
        source = "report"
    else:
        our_score = (
            (match.home_score if home_ours else match.away_score)
            if match.home_score is not None and match.away_score is not None
            else 0
        )
        opp_score = (
            (match.away_score if home_ours else match.home_score)
            if match.home_score is not None and match.away_score is not None
            else 0
        )
        source = "calendar" if match.home_score is not None else "none"

    home_score = our_score if home_ours else opp_score
    away_score = opp_score if home_ours else our_score
    score_mismatch = False
    if use_report and match.home_score is not None and match.away_score is not None:
        score_mismatch = (
            match.home_score != home_score or match.away_score != away_score
        )

    top_scorer = None
    if report:
        candidates = [
            line for line in report.lines if line.team_side == "ours" and line.played
        ]
        if candidates:
            best = max(candidates, key=lambda line: line.total)
            top_scorer = {
                "player_id": best.player_id,
                "name": (
                    f"{best.player.first_name} {best.player.last_name}".strip()
                    if best.player
                    else best.player_name
                ),
                "jersey_number": best.jersey_number,
                "total": best.total,
            }

    return {
        "id": match.id,
        "date": match.match_date,
        "time": match.match_time,
        "competition": match.competition,
        "matchday": match.matchday,
        "federation": match.federation.code if match.federation else "",
        "federation_id": match.federation_id,
        "home": home_ours,
        "opponent": _team_brief(opponent),
        "home_team": _team_brief(match.home_team),
        "away_team": _team_brief(match.away_team),
        "venue": (
            {
                "id": match.venue.id,
                "name": match.venue.name,
                "maps_url": match.venue.maps_url,
            }
            if match.venue
            else None
        ),
        "published": match.published,
        "calendar_score": {
            "home": match.home_score,
            "away": match.away_score,
        },
        "our_score": our_score,
        "opp_score": opp_score,
        "score_source": source,
        "score_mismatch": score_mismatch,
        "result": _result(our_score, opp_score) if source != "none" else None,
        "quarters": {
            "ours": ours_q if use_report else None,
            "opp": opp_q if use_report else None,
        },
        "progressive": {
            "ours": _progressive(ours_q) if use_report else None,
            "opp": _progressive(opp_q) if use_report else None,
        },
        "has_report": has_report,
        "report_id": report.id if report else None,
        "report_status": report.status if report else None,
        "report_updated_at": report.updated_at if report else None,
        "top_scorer": top_scorer,
        "has_convocations": bool(match.convocations),
        "convocations_count": len(match.convocations),
    }


def _report_out(match: Match, report: MatchReport | None) -> dict:
    lines = [_line_out(line) for line in report.lines] if report else []
    ours_q, opp_q = _report_totals(report)
    return {
        "id": report.id if report else None,
        "match_id": match.id,
        "status": report.status if report else "draft",
        "notes": report.notes if report else None,
        "created_at": report.created_at if report else None,
        "updated_at": report.updated_at if report else None,
        "lines": lines,
        "our_lines": [line for line in lines if line["team_side"] == "ours"],
        "opponent_lines": [
            line for line in lines if line["team_side"] == "opponent"
        ],
        "totals": {
            "ours": ours_q,
            "opp": opp_q,
            "our_total": sum(ours_q),
            "opp_total": sum(opp_q),
            "progressive_ours": _progressive(ours_q),
            "progressive_opp": _progressive(opp_q),
        },
    }


def _draft_lines(match: Match) -> list[MatchReportLine]:
    convocations = sorted(
        match.convocations,
        key=lambda c: (
            0 if c.kind == "starter" else 1,
            c.slot_order if c.slot_order is not None else 99,
            c.player.last_name if c.player else "",
        ),
    )
    lines: list[MatchReportLine] = []
    for index, convocation in enumerate(convocations):
        if not convocation.player:
            continue
        player = convocation.player
        lines.append(
            MatchReportLine(
                team_side="ours",
                player_id=player.id,
                player_name=f"{player.first_name} {player.last_name}".strip(),
                jersey_number=player.jersey_number,
                played=True,
                q1=0,
                q2=0,
                q3=0,
                q4=0,
                sort_order=index,
            )
        )
    return lines


def _eligible_players(db: Session, match: Match) -> list[dict]:
    code = match.federation.code if match.federation else ""
    players = db.scalars(
        select(Player)
        .options(selectinload(Player.federations))
        .where(Player.active.is_(True))
        .order_by(Player.role, Player.last_name, Player.first_name)
    ).all()
    eligible = [
        player
        for player in players
        if not code or any(f.code == code for f in player.federations)
    ]
    if not eligible:
        eligible = list(players)
    return [_player_brief(player) for player in eligible]


def _opponent_suggestions(db: Session, match: Match, opponent: Team | None) -> list[dict]:
    if not opponent:
        return []
    rows = db.execute(
        select(
            MatchReportLine.player_name,
            MatchReportLine.jersey_number,
            func.count(MatchReportLine.id).label("games"),
        )
        .join(MatchReport, MatchReport.id == MatchReportLine.report_id)
        .join(Match, Match.id == MatchReport.match_id)
        .where(
            MatchReportLine.team_side == "opponent",
            or_(
                Match.home_team_id == opponent.id,
                Match.away_team_id == opponent.id,
            ),
        )
        .group_by(MatchReportLine.player_name, MatchReportLine.jersey_number)
        .order_by(func.count(MatchReportLine.id).desc())
        .limit(40)
    ).all()
    return [
        {
            "player_name": row.player_name,
            "jersey_number": row.jersey_number,
            "games": row.games,
        }
        for row in rows
    ]


def _build_report_payload(db: Session, match: Match) -> dict:
    report = match.report
    lines = report.lines if report else _draft_lines(match)
    our_team = _our_team(db)
    home_ours = bool(match.home_team.is_ours)
    opponent = match.away_team if home_ours else match.home_team
    warnings: list[str] = []
    if not match.convocations:
        warnings.append(
            "Questa gara non ha convocazioni nel calendario: puoi comunque aggiungere i giocatori a mano."
        )
    if report and report.status == "draft":
        warnings.append("Il referto è una bozza: non entra nelle statistiche finché non lo salvi come definitivo.")
    if report and report.lines and not any(
        line.team_side == "opponent" for line in report.lines
    ):
        warnings.append("Non ci sono righe per la squadra avversaria.")

    return {
        "match": _match_summary(match, our_team),
        "report": {
            "id": report.id if report else None,
            "match_id": match.id,
            "status": report.status if report else "draft",
            "notes": report.notes if report else None,
            "created_at": report.created_at if report else None,
            "updated_at": report.updated_at if report else None,
            "lines": [_line_out(line) for line in lines],
            "totals": _report_out(match, report)["totals"],
        },
        "eligible_players": _eligible_players(db, match),
        "convocations": [
            {
                "player_id": convocation.player_id,
                "player": _player_brief(convocation.player),
                "kind": convocation.kind,
                "slot_order": convocation.slot_order,
            }
            for convocation in match.convocations
        ],
        "opponent_suggestions": _opponent_suggestions(db, match, opponent),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Board / referti
# ---------------------------------------------------------------------------


@router.get("/reports/board")
def reports_board(
    season: str | None = Query(None),
    federation: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    label = _season_label(db, season)
    span = season_range(label)
    stmt = (
        select(Match)
        .options(*_match_options())
        .order_by(Match.match_date, Match.match_time, Match.id)
    )
    if span:
        stmt = stmt.where(Match.match_date.between(*span))
    if federation:
        stmt = stmt.join(Match.federation).where(
            Federation.code == federation.upper()
        )
    matches = list(db.scalars(stmt).all())
    our_team = _our_team(db)
    summaries = [_match_summary(match, our_team) for match in matches]

    opponents: dict[int, dict] = {}
    for summary in summaries:
        opponent = summary.get("opponent")
        if opponent:
            opponents[opponent["id"]] = opponent

    seasons_rows = db.scalars(select(Match.match_date)).all()
    seasons = sorted(
        {
            current_season_label(value)
            for value in seasons_rows
            if isinstance(value, date)
        }
    )

    return {
        "season_label": label,
        "our_team": _team_brief(our_team),
        "matches": summaries,
        "opponents": sorted(opponents.values(), key=lambda item: item["name"]),
        "seasons": seasons,
    }


@router.get("/reports/stats")
def reports_stats(
    season: str | None = Query(None),
    federation: str | None = Query(None),
    opponent_id: int | None = Query(None),
    venue: str | None = Query(None, pattern="^(home|away)$"),
    result: str | None = Query(None, pattern="^(W|L|D)$"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    include_drafts: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict:
    label = _season_label(db, season)
    span = season_range(label)
    stmt = select(Match).join(MatchReport).options(*_match_options())
    if span:
        stmt = stmt.where(Match.match_date.between(*span))
    if federation:
        stmt = stmt.join(Match.federation).where(
            Federation.code == federation.upper()
        )
    if opponent_id:
        stmt = stmt.where(
            or_(
                Match.home_team_id == opponent_id,
                Match.away_team_id == opponent_id,
            )
        )
    if date_from:
        stmt = stmt.where(Match.match_date >= date_from)
    if date_to:
        stmt = stmt.where(Match.match_date <= date_to)
    if not include_drafts:
        stmt = stmt.where(MatchReport.status == "final")
    stmt = stmt.order_by(Match.match_date, Match.match_time, Match.id)
    matches = list(db.scalars(stmt).all())

    our_team = _our_team(db)
    pairs: list[tuple[Match, dict]] = []
    for match in matches:
        home_ours = bool(match.home_team.is_ours)
        if venue == "home" and not home_ours:
            continue
        if venue == "away" and home_ours:
            continue
        summary = _match_summary(match, our_team)
        if result and summary["result"] != result:
            continue
        pairs.append((match, summary))

    summaries = [summary for _, summary in pairs]
    all_players = {
        player.id: player
        for player in db.scalars(select(Player)).all()
    }

    # Convocazioni relative alle stesse gare del filtro.
    match_ids = [match.id for match, _ in pairs]
    conv_counts: dict[int, int] = {}
    if match_ids:
        rows = db.execute(
            select(Convocation.player_id, func.count(Convocation.id))
            .where(Convocation.match_id.in_(match_ids))
            .group_by(Convocation.player_id)
        ).all()
        conv_counts = {player_id: count for player_id, count in rows}

    players: dict[int, dict] = {}
    unmatched: dict[str, dict] = {}
    for match, summary in pairs:
        report = match.report
        if not report:
            continue
        for line in report.lines:
            if line.team_side != "ours" or not line.played:
                continue
            if not line.player_id:
                key = (line.player_name or "").strip().lower()
                if key:
                    row = unmatched.setdefault(
                        key,
                        {
                            "player_name": line.player_name,
                            "jersey_number": line.jersey_number,
                            "games": 0,
                            "points": 0,
                        },
                    )
                    row["games"] += 1
                    row["points"] += line.total
                continue
            player = line.player or all_players.get(line.player_id)
            if not player:
                continue
            aggregate = players.setdefault(
                player.id,
                {
                    "player_id": player.id,
                    "name": f"{player.first_name} {player.last_name}".strip(),
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                    "role": player.role,
                    "role2_type": player.role2_type,
                    "jersey_number": line.jersey_number
                    if line.jersey_number is not None
                    else player.jersey_number,
                    "photo_url": player.photo_url,
                    "games": 0,
                    "points": 0,
                    "q": [0, 0, 0, 0],
                    "best_games": [],
                    "convocations": conv_counts.get(player.id, 0),
                },
            )
            aggregate["games"] += 1
            aggregate["points"] += line.total
            for index in range(4):
                aggregate["q"][index] += getattr(line, QUARTERS[index]) or 0
            aggregate["best_games"].append(
                {
                    "match_id": match.id,
                    "date": match.match_date,
                    "federation": summary["federation"],
                    "opponent": summary["opponent"]["name"]
                    if summary["opponent"]
                    else "",
                    "opponent_id": summary["opponent"]["id"]
                    if summary["opponent"]
                    else None,
                    "home": summary["home"],
                    "result": summary["result"],
                    "our_score": summary["our_score"],
                    "opp_score": summary["opp_score"],
                    "total": line.total,
                    "quarters": [
                        line.q1 or 0,
                        line.q2 or 0,
                        line.q3 or 0,
                        line.q4 or 0,
                    ],
                }
            )

    player_rows = list(players.values())
    for row in player_rows:
        games = row["games"]
        row["avg"] = round(row["points"] / games, 2) if games else 0
        row["q_avg"] = [
            round(value / games, 2) if games else 0 for value in row["q"]
        ]
        row["best_games"].sort(key=lambda item: item["total"], reverse=True)
        row["best_games"] = row["best_games"][:8]
        row["max"] = row["best_games"][0]["total"] if row["best_games"] else 0
        row["max_game"] = row["best_games"][0] if row["best_games"] else None
        row["participation"] = (
            round(games / row["convocations"], 3)
            if row["convocations"]
            else None
        )
    player_rows.sort(key=lambda item: (item["points"], item["avg"]), reverse=True)

    top_single_games: list[dict] = []
    for row in player_rows:
        for game in row["best_games"]:
            top_single_games.append(
                {
                    **game,
                    "player_id": row["player_id"],
                    "player_name": row["name"],
                    "role": row["role"],
                    "jersey_number": row["jersey_number"],
                }
            )
    top_single_games.sort(key=lambda item: item["total"], reverse=True)

    # Avversari
    opponents: dict[int, dict] = {}
    for match, summary in pairs:
        opponent = summary.get("opponent")
        if not opponent:
            continue
        row = opponents.setdefault(
            opponent["id"],
            {
                "team_id": opponent["id"],
                "name": opponent["name"],
                "logo_url": opponent.get("logo_url"),
                "games": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "points_for": 0,
                "points_against": 0,
                "best_for": None,
                "worst_against": None,
                "last_result": None,
                "_scorers": {},
            },
        )
        row["games"] += 1
        row["points_for"] += summary["our_score"]
        row["points_against"] += summary["opp_score"]
        if summary["result"] == "W":
            row["wins"] += 1
        elif summary["result"] == "L":
            row["losses"] += 1
        else:
            row["draws"] += 1
        if not row["best_for"] or summary["our_score"] > row["best_for"]["score"]:
            row["best_for"] = {
                "score": summary["our_score"],
                "date": match.match_date,
                "match_id": match.id,
            }
        if (
            not row["worst_against"]
            or summary["opp_score"] > row["worst_against"]["score"]
        ):
            row["worst_against"] = {
                "score": summary["opp_score"],
                "date": match.match_date,
                "match_id": match.id,
            }
        row["last_result"] = {
            "result": summary["result"],
            "our_score": summary["our_score"],
            "opp_score": summary["opp_score"],
            "date": match.match_date,
        }
        if match.report:
            for line in match.report.lines:
                if line.team_side == "ours" and line.player_id:
                    row["_scorers"][line.player_id] = (
                        row["_scorers"].get(line.player_id, 0) + line.total
                    )

    opponent_rows = list(opponents.values())
    for row in opponent_rows:
        row["avg_for"] = (
            round(row["points_for"] / row["games"], 1) if row["games"] else 0
        )
        row["avg_against"] = (
            round(row["points_against"] / row["games"], 1) if row["games"] else 0
        )
        row["diff"] = row["points_for"] - row["points_against"]
        scorer_id = (
            max(row["_scorers"], key=row["_scorers"].get)
            if row["_scorers"]
            else None
        )
        scorer = all_players.get(scorer_id) if scorer_id else None
        row["top_scorer"] = (
            {
                "player_id": scorer.id,
                "name": f"{scorer.first_name} {scorer.last_name}".strip(),
                "points": row["_scorers"][scorer.id],
            }
            if scorer
            else None
        )
        del row["_scorers"]
    opponent_rows.sort(key=lambda item: (-item["games"], item["name"]))

    # Riepilogo squadra
    games = len(summaries)
    wins = sum(1 for summary in summaries if summary["result"] == "W")
    losses = sum(1 for summary in summaries if summary["result"] == "L")
    draws = sum(1 for summary in summaries if summary["result"] == "D")
    points_for = sum(summary["our_score"] for summary in summaries)
    points_against = sum(summary["opp_score"] for summary in summaries)
    quarters_ours = [
        sum(
            (summary["quarters"]["ours"] or [0, 0, 0, 0])[index]
            for summary in summaries
        )
        for index in range(4)
    ]
    quarters_opp = [
        sum(
            (summary["quarters"]["opp"] or [0, 0, 0, 0])[index]
            for summary in summaries
        )
        for index in range(4)
    ]

    def _home_away(flag: bool) -> dict:
        subset = [summary for summary in summaries if summary["home"] is flag]
        return {
            "games": len(subset),
            "wins": sum(1 for summary in subset if summary["result"] == "W"),
            "losses": sum(1 for summary in subset if summary["result"] == "L"),
            "draws": sum(1 for summary in subset if summary["result"] == "D"),
            "points_for": sum(summary["our_score"] for summary in subset),
            "points_against": sum(summary["opp_score"] for summary in subset),
        }

    fed_split: dict[str, dict] = {}
    for summary in summaries:
        code = summary["federation"] or "—"
        row = fed_split.setdefault(
            code,
            {
                "code": code,
                "games": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "points_for": 0,
                "points_against": 0,
            },
        )
        row["games"] += 1
        row["points_for"] += summary["our_score"]
        row["points_against"] += summary["opp_score"]
        if summary["result"] == "W":
            row["wins"] += 1
        elif summary["result"] == "L":
            row["losses"] += 1
        else:
            row["draws"] += 1

    current_streak_type = None
    current_streak = 0
    for summary in reversed(summaries):
        if current_streak_type is None:
            current_streak_type = summary["result"]
            current_streak = 1
        elif summary["result"] == current_streak_type:
            current_streak += 1
        else:
            break

    longest_win = 0
    longest_loss = 0
    run_type = None
    run = 0
    for summary in summaries:
        if summary["result"] == run_type:
            run += 1
        else:
            run_type = summary["result"]
            run = 1
        if run_type == "W":
            longest_win = max(longest_win, run)
        elif run_type == "L":
            longest_loss = max(longest_loss, run)

    last5 = summaries[-5:]
    prev5 = summaries[-10:-5]
    avg = lambda rows, key: (
        round(sum(row[key] for row in rows) / len(rows), 1) if rows else 0
    )

    best_games = sorted(
        summaries, key=lambda summary: summary["our_score"] - summary["opp_score"], reverse=True
    )[:3]
    worst_games = sorted(
        summaries, key=lambda summary: summary["our_score"] - summary["opp_score"]
    )[:3]
    best_quarter_index = (
        max(range(4), key=lambda index: quarters_ours[index]) if games else 0
    )
    worst_quarter_index = (
        min(range(4), key=lambda index: quarters_ours[index]) if games else 0
    )

    convocation_leaders = [
        {
            "player_id": player_id,
            "name": (
                f"{all_players[player_id].first_name} {all_players[player_id].last_name}".strip()
                if player_id in all_players
                else f"#{player_id}"
            ),
            "role": all_players[player_id].role if player_id in all_players else None,
            "jersey_number": all_players[player_id].jersey_number
            if player_id in all_players
            else None,
            "convocations": count,
        }
        for player_id, count in sorted(
            conv_counts.items(), key=lambda item: item[1], reverse=True
        )[:8]
    ]

    return {
        "generated_at": datetime.now(),
        "filters": {
            "season": label,
            "federation": federation,
            "opponent_id": opponent_id,
            "venue": venue,
            "result": result,
            "date_from": date_from,
            "date_to": date_to,
            "include_drafts": include_drafts,
        },
        "summary": {
            "games": games,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "points_for": points_for,
            "points_against": points_against,
            "diff": points_for - points_against,
            "avg_for": round(points_for / games, 1) if games else 0,
            "avg_against": round(points_against / games, 1) if games else 0,
            "avg_diff": round((points_for - points_against) / games, 1)
            if games
            else 0,
            "quarters": {
                "ours": quarters_ours,
                "opp": quarters_opp,
                "diff": [
                    quarters_ours[index] - quarters_opp[index]
                    for index in range(4)
                ],
            },
            "quarter_avg": {
                "ours": [
                    round(value / games, 1) if games else 0
                    for value in quarters_ours
                ],
                "opp": [
                    round(value / games, 1) if games else 0
                    for value in quarters_opp
                ],
            },
            "home": _home_away(True),
            "away": _home_away(False),
            "federation_split": sorted(
                fed_split.values(), key=lambda item: item["code"]
            ),
            "current_streak": {
                "type": current_streak_type,
                "count": current_streak,
            },
            "longest_win_streak": longest_win,
            "longest_loss_streak": longest_loss,
            "last5": {
                "games": len(last5),
                "avg_for": avg(last5, "our_score"),
                "avg_against": avg(last5, "opp_score"),
            },
            "prev5": {
                "games": len(prev5),
                "avg_for": avg(prev5, "our_score"),
                "avg_against": avg(prev5, "opp_score"),
            },
            "best_games": best_games,
            "worst_games": worst_games,
            "best_quarter": {
                "quarter": best_quarter_index + 1,
                "points": quarters_ours[best_quarter_index] if games else 0,
            },
            "worst_quarter": {
                "quarter": worst_quarter_index + 1,
                "points": quarters_ours[worst_quarter_index] if games else 0,
            },
        },
        "trend": [
            {
                "match_id": summary["id"],
                "date": summary["date"],
                "opponent": summary["opponent"]["name"]
                if summary["opponent"]
                else "",
                "home": summary["home"],
                "federation": summary["federation"],
                "our_score": summary["our_score"],
                "opp_score": summary["opp_score"],
                "diff": summary["our_score"] - summary["opp_score"],
                "result": summary["result"],
                "quarters": summary["quarters"],
            }
            for summary in summaries
        ],
        "matches": summaries,
        "players": player_rows,
        "top_scorers": player_rows[:6],
        "top_single_games": top_single_games[:10],
        "opponents": opponent_rows,
        "convocation_leaders": convocation_leaders,
        "convocations": {
            "total": sum(conv_counts.values()),
            "average_per_match": round(
                sum(conv_counts.values()) / games, 1
            )
            if games
            else 0,
        },
        "unmatched": list(unmatched.values()),
    }


@router.get("/reports/players/{player_id}")
def report_player_detail(
    player_id: int,
    season: str | None = Query(None),
    federation: str | None = Query(None),
    opponent_id: int | None = Query(None),
    include_drafts: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict:
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Giocatore non trovato")
    label = _season_label(db, season)
    span = season_range(label)
    stmt = (
        select(Match)
        .join(MatchReport)
        .join(MatchReportLine)
        .options(*_match_options())
        .where(
            MatchReportLine.player_id == player_id,
            MatchReportLine.team_side == "ours",
        )
    )
    if span:
        stmt = stmt.where(Match.match_date.between(*span))
    if federation:
        stmt = stmt.join(Match.federation).where(
            Federation.code == federation.upper()
        )
    if opponent_id:
        stmt = stmt.where(
            or_(
                Match.home_team_id == opponent_id,
                Match.away_team_id == opponent_id,
            )
        )
    if not include_drafts:
        stmt = stmt.where(MatchReport.status == "final")
    stmt = stmt.order_by(Match.match_date, Match.match_time, Match.id)
    matches = list(db.scalars(stmt).unique().all())

    our_team = _our_team(db)
    games: list[dict] = []
    conv_counts = 0
    if matches:
        conv_counts = (
            db.scalar(
                select(func.count(Convocation.id)).where(
                    Convocation.player_id == player_id,
                    Convocation.match_id.in_([match.id for match in matches]),
                )
            )
            or 0
        )
    for match in matches:
        summary = _match_summary(match, our_team)
        line = next(
            (
                item
                for item in (match.report.lines if match.report else [])
                if item.player_id == player_id and item.team_side == "ours"
            ),
            None,
        )
        if not line:
            continue
        games.append(
            {
                "match_id": match.id,
                "date": match.match_date,
                "federation": summary["federation"],
                "opponent": summary["opponent"]["name"]
                if summary["opponent"]
                else "",
                "opponent_id": summary["opponent"]["id"]
                if summary["opponent"]
                else None,
                "home": summary["home"],
                "result": summary["result"],
                "our_score": summary["our_score"],
                "opp_score": summary["opp_score"],
                "quarters": [line.q1 or 0, line.q2 or 0, line.q3 or 0, line.q4 or 0],
                "total": line.total,
                "played": line.played,
                "fouls": line.fouls,
                "rebounds": line.rebounds,
                "assists": line.assists,
                "steals": line.steals,
                "turnovers": line.turnovers,
                "blocks": line.blocks,
                "minutes": line.minutes,
            }
        )

    played_games = [game for game in games if game["played"]]
    points = sum(game["total"] for game in played_games)
    q_totals = [
        sum(game["quarters"][index] for game in played_games) for index in range(4)
    ]
    best_games = sorted(played_games, key=lambda game: game["total"], reverse=True)
    by_opponent: dict[int, dict] = {}
    for game in played_games:
        key = game["opponent_id"] or 0
        row = by_opponent.setdefault(
            key,
            {
                "opponent_id": game["opponent_id"],
                "opponent": game["opponent"],
                "games": 0,
                "points": 0,
                "max": 0,
                "wins": 0,
                "losses": 0,
            },
        )
        row["games"] += 1
        row["points"] += game["total"]
        row["max"] = max(row["max"], game["total"])
        if game["result"] == "W":
            row["wins"] += 1
        elif game["result"] == "L":
            row["losses"] += 1
    opponent_rows = list(by_opponent.values())
    for row in opponent_rows:
        row["avg"] = round(row["points"] / row["games"], 1) if row["games"] else 0
    opponent_rows.sort(key=lambda item: (-item["points"], item["opponent"]))

    by_federation: dict[str, dict] = {}
    for game in played_games:
        code = game["federation"] or "—"
        row = by_federation.setdefault(
            code, {"code": code, "games": 0, "points": 0}
        )
        row["games"] += 1
        row["points"] += game["total"]
    for row in by_federation.values():
        row["avg"] = round(row["points"] / row["games"], 1) if row["games"] else 0

    return {
        "player": _player_brief(player),
        "season": label,
        "summary": {
            "games": len(played_games),
            "convocations": conv_counts,
            "participation": round(len(played_games) / conv_counts, 3)
            if conv_counts
            else None,
            "points": points,
            "avg": round(points / len(played_games), 2) if played_games else 0,
            "max": best_games[0]["total"] if best_games else 0,
            "max_game": best_games[0] if best_games else None,
            "quarters": q_totals,
            "quarter_avg": [
                round(value / len(played_games), 2) if played_games else 0
                for value in q_totals
            ],
            "wins": sum(1 for game in played_games if game["result"] == "W"),
            "losses": sum(1 for game in played_games if game["result"] == "L"),
            "draws": sum(1 for game in played_games if game["result"] == "D"),
        },
        "games": games,
        "recent": list(reversed(games)),
        "best_games": best_games[:5],
        "opponents": opponent_rows,
        "federations": sorted(by_federation.values(), key=lambda item: item["code"]),
        "trend": [
            {
                "date": game["date"],
                "opponent": game["opponent"],
                "total": game["total"],
                "result": game["result"],
            }
            for game in games
        ],
    }


@router.get("/reports/{match_id}")
def get_report(match_id: int, db: Session = Depends(get_db)) -> dict:
    match = _load_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Gara non trovata")
    return _build_report_payload(db, match)


@router.put("/reports/{match_id}")
def save_report(
    match_id: int,
    payload: schemas.ReportIn,
    db: Session = Depends(get_db),
) -> dict:
    match = _load_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Gara non trovata")
    if payload.status not in ("draft", "final"):
        raise HTTPException(status_code=400, detail="Stato referto non valido")

    report = match.report
    if not report:
        report = MatchReport(match_id=match.id)
        db.add(report)
        db.flush()

    for old in list(report.lines):
        db.delete(old)
    db.flush()

    seen_players: set[int] = set()
    players_cache: dict[int, Player] = {}
    for index, item in enumerate(payload.lines):
        side = "opponent" if item.team_side == "opponent" else "ours"
        player = None
        if side == "ours" and item.player_id:
            if item.player_id in seen_players:
                raise HTTPException(
                    status_code=400,
                    detail="Lo stesso giocatore compare due volte nel referto",
                )
            seen_players.add(item.player_id)
            player = players_cache.get(item.player_id) or db.get(Player, item.player_id)
            if not player:
                raise HTTPException(
                    status_code=400,
                    detail=f"Giocatore {item.player_id} non trovato",
                )
            players_cache[player.id] = player
            if item.jersey_number is not None and player.jersey_number is None:
                player.jersey_number = item.jersey_number

        name = (
            f"{player.first_name} {player.last_name}".strip()
            if player
            else (item.player_name or "").strip()
        )
        if not name:
            raise HTTPException(
                status_code=400,
                detail="Ogni riga del referto deve avere un nome giocatore",
            )
        line = MatchReportLine(
            report_id=report.id,
            team_side=side,
            player_id=player.id if player else None,
            player_name=name,
            jersey_number=item.jersey_number
            if item.jersey_number is not None
            else (player.jersey_number if player else None),
            played=bool(item.played),
            q1=max(0, int(item.q1 or 0)),
            q2=max(0, int(item.q2 or 0)),
            q3=max(0, int(item.q3 or 0)),
            q4=max(0, int(item.q4 or 0)),
            fouls=item.fouls,
            rebounds=item.rebounds,
            assists=item.assists,
            steals=item.steals,
            turnovers=item.turnovers,
            blocks=item.blocks,
            minutes=item.minutes,
            notes=item.notes,
            sort_order=item.sort_order or index,
        )
        db.add(line)

    report.status = payload.status
    report.notes = payload.notes
    db.flush()

    # Calcola i totali dal payload: il relationship report.lines potrebbe non
    # riflettere ancora le righe appena aggiunte nella stessa transazione.
    ours_q = [
        sum(
            max(0, int(getattr(item, quarter) or 0))
            for item in payload.lines
            if item.team_side != "opponent"
        )
        for quarter in QUARTERS
    ]
    opp_q = [
        sum(
            max(0, int(getattr(item, quarter) or 0))
            for item in payload.lines
            if item.team_side == "opponent"
        )
        for quarter in QUARTERS
    ]
    our_total = sum(ours_q)
    opp_total = sum(opp_q)
    if payload.sync_score and report.status == "final":
        if match.home_team.is_ours:
            match.home_score = our_total
            match.away_score = opp_total
        else:
            match.home_score = opp_total
            match.away_score = our_total
    db.commit()

    match = _load_match(db, match_id)
    return _build_report_payload(db, match)


@router.delete("/reports/{match_id}", status_code=204)
def delete_report(match_id: int, db: Session = Depends(get_db)) -> None:
    report = db.scalars(
        select(MatchReport).where(MatchReport.match_id == match_id)
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Referto non trovato")
    db.delete(report)
    db.commit()


# ---------------------------------------------------------------------------
# Import Excel / sync calendario
# ---------------------------------------------------------------------------


@router.post("/reports/parse-excel")
async def parse_excel(
    match_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    match = _load_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Gara non trovata")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File vuoto")
    if len(content) > 12 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File troppo grande (max 12 MB)")
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=400,
            detail="Formato non supportato: carica un file .xlsx",
        )

    players = db.scalars(select(Player)).all()
    player_dicts = [
        {
            "id": player.id,
            "first_name": player.first_name,
            "last_name": player.last_name,
            "role": player.role,
            "jersey_number": player.jersey_number,
        }
        for player in players
    ]
    home_ours = bool(match.home_team.is_ours)
    opponent = match.away_team if home_ours else match.home_team
    try:
        parsed = parse_workbook(
            content,
            player_dicts,
            opponent_name=opponent.name if opponent else "",
            federation_code=match.federation.code if match.federation else "",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail=f"Impossibile leggere il file Excel: {exc}"
        ) from exc

    parsed["file_name"] = file.filename
    parsed["match"] = _match_summary(match, _our_team(db))
    parsed["eligible_players"] = _eligible_players(db, match)
    return parsed


@router.post("/sync-public")
def sync_public_calendar(db: Session = Depends(get_db)) -> dict:
    try:
        return sync_from_public(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
