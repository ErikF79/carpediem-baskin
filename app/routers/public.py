from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import schemas
from ..config import settings
from ..database import get_db
from ..models import Federation, Match, Player, Team, Unavailability, Venue

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/config")
def get_config(db: Session = Depends(get_db)) -> dict:
    federations = db.scalars(select(Federation).order_by(Federation.id)).all()
    our_team = db.scalars(select(Team).where(Team.is_ours.is_(True))).first()
    return {
        "app_name": settings.app_name,
        "federations": [schemas.FederationOut.model_validate(f) for f in federations],
        "our_team": schemas.TeamOut.model_validate(our_team) if our_team else None,
    }


@router.get("/federations", response_model=list[schemas.FederationOut])
def list_federations(db: Session = Depends(get_db)):
    return db.scalars(select(Federation).order_by(Federation.id)).all()


@router.get("/teams", response_model=list[schemas.TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.scalars(select(Team).order_by(Team.name)).all()


@router.get("/venues", response_model=list[schemas.VenueOut])
def list_venues(db: Session = Depends(get_db)):
    return db.scalars(select(Venue).order_by(Venue.name)).all()


@router.get("/players", response_model=list[schemas.PlayerOut])
def list_players(
    active_only: bool = Query(True), db: Session = Depends(get_db)
):
    stmt = (
        select(Player)
        .options(selectinload(Player.federations))
        .order_by(Player.role, Player.last_name)
    )
    if active_only:
        stmt = stmt.where(Player.active.is_(True))
    return db.scalars(stmt).all()


@router.get("/matches", response_model=list[schemas.MatchOut])
def list_matches(
    federation: str | None = Query(None, description="Codice federazione, es. EISI"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    upcoming: bool = Query(False),
    include_unpublished: bool = Query(False),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Match)
        .options(
            selectinload(Match.federation),
            selectinload(Match.home_team).selectinload(Team.federations),
            selectinload(Match.away_team).selectinload(Team.federations),
            selectinload(Match.venue),
        )
        .order_by(Match.match_date, Match.match_time)
    )
    if federation:
        stmt = stmt.join(Match.federation).where(Federation.code == federation.upper())
    if date_from:
        stmt = stmt.where(Match.match_date >= date_from)
    if date_to:
        stmt = stmt.where(Match.match_date <= date_to)
    if upcoming:
        stmt = stmt.where(Match.match_date >= date.today())
    if not include_unpublished:
        stmt = stmt.where(Match.published.is_(True))
    return db.scalars(stmt).all()


@router.get("/matches/{match_id}", response_model=schemas.MatchDetailOut)
def get_match(match_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(Match)
        .where(Match.id == match_id)
        .options(
            selectinload(Match.federation),
            selectinload(Match.home_team).selectinload(Team.federations),
            selectinload(Match.away_team).selectinload(Team.federations),
            selectinload(Match.venue),
            selectinload(Match.convocations),
        )
    )
    match = db.scalars(stmt).first()
    if not match:
        raise HTTPException(status_code=404, detail="Gara non trovata")
    return match


@router.get("/availability", response_model=list[schemas.UnavailabilityOut])
def list_unavailability(
    date_on: date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
    stmt = select(Unavailability).options(
        selectinload(Unavailability.player)
    )
    if date_on:
        stmt = stmt.where(Unavailability.date == date_on)
    return db.scalars(stmt.order_by(Unavailability.date)).all()
