from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
    Column,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

team_federations = Table(
    "team_federations",
    Base.metadata,
    Column("team_id", ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "federation_id",
        ForeignKey("federations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

player_federations = Table(
    "player_federations",
    Base.metadata,
    Column("player_id", ForeignKey("players.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "federation_id",
        ForeignKey("federations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

venue_teams = Table(
    "venue_teams",
    Base.metadata,
    Column("venue_id", ForeignKey("venues.id", ondelete="CASCADE"), primary_key=True),
    Column("team_id", ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
)


class Federation(Base):
    __tablename__ = "federations"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)

    teams: Mapped[list["Team"]] = relationship(
        secondary=team_federations, back_populates="federations"
    )
    matches: Mapped[list["Match"]] = relationship(back_populates="federation")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_ours: Mapped[bool] = mapped_column(Boolean, default=False)

    federations: Mapped[list["Federation"]] = relationship(
        secondary=team_federations, back_populates="teams"
    )
    venues: Mapped[list["Venue"]] = relationship(
        secondary=venue_teams, back_populates="teams"
    )


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    maps_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    matches: Mapped[list["Match"]] = relationship(back_populates="venue")
    teams: Mapped[list["Team"]] = relationship(
        secondary=venue_teams, back_populates="venues"
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    code_eisi: Mapped[str | None] = mapped_column(String(40), nullable=True)
    code_csain: Mapped[str | None] = mapped_column(String(40), nullable=True)
    role: Mapped[int] = mapped_column(Integer)  # 1..6
    role2_type: Mapped[str | None] = mapped_column(
        String(4), nullable=True
    )  # sottotipo per il ruolo 2: 2T, 2P, 2R
    jersey_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shot_distance_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)

    federations: Mapped[list["Federation"]] = relationship(
        secondary=player_federations
    )
    convocations: Mapped[list["Convocation"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    unavailabilities: Mapped[list["Unavailability"]] = relationship(
        back_populates="player", cascade="all, delete-orphan"
    )
    report_lines: Mapped[list["MatchReportLine"]] = relationship(back_populates="player")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_date: Mapped[date] = mapped_column(Date)
    match_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    federation_id: Mapped[int] = mapped_column(ForeignKey("federations.id"))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    venue_id: Mapped[int | None] = mapped_column(
        ForeignKey("venues.id"), nullable=True
    )
    competition: Mapped[str | None] = mapped_column(String(150), nullable=True)
    matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    federation: Mapped["Federation"] = relationship(back_populates="matches")
    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])
    venue: Mapped["Venue"] = relationship(back_populates="matches")
    convocations: Mapped[list["Convocation"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    transport: Mapped[list["Transport"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    report: Mapped["MatchReport | None"] = relationship(
        back_populates="match", cascade="all, delete-orphan", uselist=False
    )

    @property
    def is_played(self) -> bool:
        return self.home_score is not None and self.away_score is not None


class Convocation(Base):
    __tablename__ = "convocations"
    __table_args__ = (UniqueConstraint("match_id", "player_id", name="uq_match_player"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE")
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(20), default="starter")  # starter|reserve
    slot_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    match: Mapped["Match"] = relationship(back_populates="convocations")
    player: Mapped["Player"] = relationship(back_populates="convocations")


class Unavailability(Base):
    __tablename__ = "unavailability"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE")
    )
    date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    player: Mapped["Player"] = relationship(back_populates="unavailabilities")


class Transport(Base):
    __tablename__ = "transport"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20), default="furgone")  # furgone | auto
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    seats_total: Mapped[int] = mapped_column(Integer, default=8)  # 8 o 6
    seats_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)

    match: Mapped["Match"] = relationship(back_populates="transport")
    driver: Mapped["Player"] = relationship()


class MatchReport(Base):
    """Referto di una gara: punti per quarto di ogni giocatore delle due squadre."""

    __tablename__ = "match_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | final
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    match: Mapped["Match"] = relationship(back_populates="report")
    lines: Mapped[list["MatchReportLine"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="MatchReportLine.sort_order",
    )

    @property
    def is_final(self) -> bool:
        return self.status == "final"


class MatchReportLine(Base):
    """Riga del referto: un giocatore (nostro o avversario) con i punti nei quarti."""

    __tablename__ = "match_report_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("match_reports.id", ondelete="CASCADE")
    )
    team_side: Mapped[str] = mapped_column(String(10))  # ours | opponent
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    player_name: Mapped[str] = mapped_column(String(150))
    jersey_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    played: Mapped[bool] = mapped_column(Boolean, default=True)
    q1: Mapped[int] = mapped_column(Integer, default=0)
    q2: Mapped[int] = mapped_column(Integer, default=0)
    q3: Mapped[int] = mapped_column(Integer, default=0)
    q4: Mapped[int] = mapped_column(Integer, default=0)
    fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rebounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assists: Mapped[int | None] = mapped_column(Integer, nullable=True)
    steals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnovers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blocks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    report: Mapped["MatchReport"] = relationship(back_populates="lines")
    player: Mapped["Player | None"] = relationship(back_populates="report_lines")

    @property
    def total(self) -> int:
        return (self.q1 or 0) + (self.q2 or 0) + (self.q3 or 0) + (self.q4 or 0)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str | None] = mapped_column(String(300), nullable=True)
