import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..database import get_db
from ..models import (
    Convocation,
    Federation,
    Match,
    Player,
    Setting,
    Team,
    Unavailability,
    Venue,
)
from ..security import (
    COOKIE_NAME,
    check_password,
    make_session_token,
    require_staff,
)

auth_router = APIRouter(prefix="/api/admin", tags=["admin-auth"])
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_staff)])


@auth_router.post("/login")
def login(payload: schemas.LoginIn, response: Response) -> dict:
    if not check_password(payload.password):
        raise HTTPException(status_code=401, detail="Password errata")
    response.set_cookie(
        COOKIE_NAME,
        make_session_token(),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return {"staff": True}


@auth_router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME)
    return {"staff": False}


@router.get("/me")
def me() -> dict:
    return {"staff": True}


# ----------------------------- Federations -----------------------------

@router.post("/federations", response_model=schemas.FederationOut)
def create_federation(payload: schemas.FederationIn, db: Session = Depends(get_db)):
    obj = Federation(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/federations/{obj_id}", response_model=schemas.FederationOut)
def update_federation(
    obj_id: int, payload: schemas.FederationIn, db: Session = Depends(get_db)
):
    obj = db.get(Federation, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Federazione non trovata")
    for key, value in payload.model_dump().items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/federations/{obj_id}", status_code=204)
def delete_federation(obj_id: int, db: Session = Depends(get_db)):
    obj = db.get(Federation, obj_id)
    if obj:
        db.delete(obj)
        db.commit()


# -------------------------------- Teams --------------------------------

def _load_team(db: Session, obj_id: int) -> Team:
    stmt = (
        select(Team)
        .where(Team.id == obj_id)
        .options(selectinload(Team.federations))
    )
    return db.scalars(stmt).first()


@router.post("/teams", response_model=schemas.TeamOut)
def create_team(payload: schemas.TeamIn, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"federation_ids"})
    obj = Team(**data)
    if payload.federation_ids:
        obj.federations = db.scalars(
            select(Federation).where(Federation.id.in_(payload.federation_ids))
        ).all()
    db.add(obj)
    db.commit()
    return _load_team(db, obj.id)


@router.put("/teams/{obj_id}", response_model=schemas.TeamOut)
def update_team(
    obj_id: int, payload: schemas.TeamIn, db: Session = Depends(get_db)
):
    obj = db.get(Team, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Squadra non trovata")
    data = payload.model_dump(exclude={"federation_ids"})
    for key, value in data.items():
        setattr(obj, key, value)
    obj.federations = db.scalars(
        select(Federation).where(Federation.id.in_(payload.federation_ids))
    ).all()
    db.commit()
    return _load_team(db, obj.id)


@router.delete("/teams/{obj_id}", status_code=204)
def delete_team(obj_id: int, db: Session = Depends(get_db)):
    obj = db.get(Team, obj_id)
    if obj:
        db.delete(obj)
        db.commit()


# -------------------------------- Venues --------------------------------

def _load_venue(db: Session, obj_id: int) -> Venue:
    stmt = (
        select(Venue)
        .where(Venue.id == obj_id)
        .options(selectinload(Venue.teams))
    )
    return db.scalars(stmt).first()


def _venue_teams(db: Session, team_ids: list[int]) -> list[Team]:
    if not team_ids:
        return []
    return db.scalars(select(Team).where(Team.id.in_(team_ids))).all()


@router.post("/venues", response_model=schemas.VenueOut)
def create_venue(payload: schemas.VenueIn, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"team_ids"})
    obj = Venue(**data)
    obj.teams = _venue_teams(db, payload.team_ids)
    db.add(obj)
    db.commit()
    return _load_venue(db, obj.id)


@router.put("/venues/{obj_id}", response_model=schemas.VenueOut)
def update_venue(
    obj_id: int, payload: schemas.VenueIn, db: Session = Depends(get_db)
):
    obj = db.get(Venue, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Palestra non trovata")
    data = payload.model_dump(exclude={"team_ids"})
    for key, value in data.items():
        setattr(obj, key, value)
    obj.teams = _venue_teams(db, payload.team_ids)
    db.commit()
    return _load_venue(db, obj.id)


@router.delete("/venues/{obj_id}", status_code=204)
def delete_venue(obj_id: int, db: Session = Depends(get_db)):
    obj = db.get(Venue, obj_id)
    if obj:
        db.delete(obj)
        db.commit()


# ------------------------------- Players -------------------------------

def _load_player(db: Session, obj_id: int) -> Player:
    stmt = (
        select(Player)
        .where(Player.id == obj_id)
        .options(selectinload(Player.federations))
    )
    return db.scalars(stmt).first()


@router.post("/players", response_model=schemas.PlayerOut)
def create_player(payload: schemas.PlayerIn, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"federation_ids"})
    obj = Player(**data)
    if payload.federation_ids:
        obj.federations = db.scalars(
            select(Federation).where(Federation.id.in_(payload.federation_ids))
        ).all()
    db.add(obj)
    db.commit()
    return _load_player(db, obj.id)


@router.put("/players/{obj_id}", response_model=schemas.PlayerOut)
def update_player(
    obj_id: int, payload: schemas.PlayerIn, db: Session = Depends(get_db)
):
    obj = db.get(Player, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Giocatore non trovato")
    data = payload.model_dump(exclude={"federation_ids"})
    for key, value in data.items():
        setattr(obj, key, value)
    obj.federations = db.scalars(
        select(Federation).where(Federation.id.in_(payload.federation_ids))
    ).all()
    db.commit()
    return _load_player(db, obj.id)


@router.delete("/players/{obj_id}", status_code=204)
def delete_player(obj_id: int, db: Session = Depends(get_db)):
    obj = db.get(Player, obj_id)
    if obj:
        db.delete(obj)
        db.commit()


# -------------------------------- Matches -------------------------------

def _load_match(db: Session, obj_id: int) -> Match:
    stmt = (
        select(Match)
        .where(Match.id == obj_id)
        .options(
            selectinload(Match.federation),
            selectinload(Match.home_team).selectinload(Team.federations),
            selectinload(Match.away_team).selectinload(Team.federations),
            selectinload(Match.venue).selectinload(Venue.teams),
            selectinload(Match.convocations),
        )
    )
    return db.scalars(stmt).first()


@router.get("/matches", response_model=list[schemas.MatchOut])
def list_matches(db: Session = Depends(get_db)):
    stmt = (
        select(Match)
        .options(
            selectinload(Match.federation),
            selectinload(Match.home_team).selectinload(Team.federations),
            selectinload(Match.away_team).selectinload(Team.federations),
            selectinload(Match.venue).selectinload(Venue.teams),
        )
        .order_by(Match.match_date, Match.match_time)
    )
    return db.scalars(stmt).all()


@router.post("/matches", response_model=schemas.MatchDetailOut)
def create_match(payload: schemas.MatchIn, db: Session = Depends(get_db)):
    obj = Match(**payload.model_dump())
    db.add(obj)
    db.commit()
    return _load_match(db, obj.id)


@router.put("/matches/{obj_id}", response_model=schemas.MatchDetailOut)
def update_match(
    obj_id: int, payload: schemas.MatchIn, db: Session = Depends(get_db)
):
    obj = db.get(Match, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Gara non trovata")
    for key, value in payload.model_dump().items():
        setattr(obj, key, value)
    db.commit()
    return _load_match(db, obj.id)


@router.delete("/matches/{obj_id}", status_code=204)
def delete_match(obj_id: int, db: Session = Depends(get_db)):
    obj = db.get(Match, obj_id)
    if obj:
        db.delete(obj)
        db.commit()


_SEASON_RE = re.compile(r"^\s*(\d{4})\s*[/\-]\s*(\d{4})\s*$")


def _season_range(label: str | None) -> tuple[date, date] | None:
    """Intervallo di date della stagione (1 luglio - 30 giugno)."""
    if not label:
        return None
    m = _SEASON_RE.match(label)
    if not m:
        return None
    start_year, end_year = int(m.group(1)), int(m.group(2))
    return date(start_year, 7, 1), date(end_year, 6, 30)


@router.get("/settings/season")
def get_season(db: Session = Depends(get_db)) -> dict:
    obj = db.get(Setting, "season_label")
    return {"season_label": obj.value if obj else None}


@router.put("/settings/season")
def set_season(payload: schemas.SeasonIn, db: Session = Depends(get_db)) -> dict:
    value = (payload.season_label or "").strip() or None
    if value and not _SEASON_RE.match(value):
        raise HTTPException(
            status_code=400, detail="Formato stagione non valido (es. 2026/2027)"
        )
    obj = db.get(Setting, "season_label")
    if obj:
        obj.value = value
    else:
        db.add(Setting(key="season_label", value=value))
    db.commit()
    return {"season_label": value}


@router.get("/convocations/stats")
def convocation_stats(db: Session = Depends(get_db)) -> dict[str, dict[str, int]]:
    """Numero di convocazioni per giocatore, distinto per federazione.

    Se e impostata una stagione (es. 2026/2027), contano solo le gare di quella stagione.
    """
    season = db.get(Setting, "season_label")
    stmt = (
        select(
            Convocation.player_id,
            Federation.code,
            func.count(Convocation.id),
        )
        .join(Match, Match.id == Convocation.match_id)
        .join(Federation, Federation.id == Match.federation_id)
        .group_by(Convocation.player_id, Federation.code)
    )
    span = _season_range(season.value if season else None)
    if span:
        stmt = stmt.where(Match.match_date.between(*span))
    stats: dict[str, dict[str, int]] = {}
    for player_id, code, count in db.execute(stmt):
        stats.setdefault(str(player_id), {})[code] = count
    return stats


@router.put(
    "/matches/{obj_id}/convocations", response_model=schemas.MatchDetailOut
)
def set_convocations(
    obj_id: int,
    payload: schemas.ConvocationsIn,
    db: Session = Depends(get_db),
):
    obj = db.get(Match, obj_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Gara non trovata")
    for old in list(obj.convocations):
        db.delete(old)
    db.flush()
    for item in payload.items:
        db.add(
            Convocation(
                match_id=obj_id,
                player_id=item.player_id,
                kind=item.kind,
                slot_order=item.slot_order,
            )
        )
    db.commit()
    return _load_match(db, obj_id)


# ---------------------------- Unavailability ----------------------------

@router.post("/unavailability", response_model=schemas.UnavailabilityOut)
def create_unavailability(
    payload: schemas.UnavailabilityIn, db: Session = Depends(get_db)
):
    obj = Unavailability(**payload.model_dump())
    db.add(obj)
    db.flush()
    # Se il giocatore era convocato in una gara di quella data, lo si rimuove.
    db.execute(
        delete(Convocation).where(
            Convocation.player_id == payload.player_id,
            Convocation.match_id.in_(
                select(Match.id).where(Match.match_date == payload.date)
            ),
        )
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/unavailability/{obj_id}", status_code=204)
def delete_unavailability(obj_id: int, db: Session = Depends(get_db)):
    obj = db.get(Unavailability, obj_id)
    if obj:
        db.delete(obj)
        db.commit()
