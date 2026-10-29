from datetime import date, time

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FederationOut(ORMModel):
    id: int
    code: str
    name: str
    logo_url: str | None = None
    color: str | None = None


class TeamOut(ORMModel):
    id: int
    name: str
    logo_url: str | None = None
    city: str | None = None
    is_ours: bool
    federations: list[FederationOut] = []


class TeamBrief(ORMModel):
    id: int
    name: str
    logo_url: str | None = None
    city: str | None = None
    is_ours: bool


class VenueOut(ORMModel):
    id: int
    name: str
    address: str | None = None
    maps_url: str | None = None
    teams: list[TeamBrief] = []


class PlayerOut(ORMModel):
    id: int
    first_name: str
    last_name: str
    photo_url: str | None = None
    code_eisi: str | None = None
    code_csain: str | None = None
    role: int
    role2_type: str | None = None
    shot_distance_cm: int | None = None
    active: bool
    email: str | None = None
    phone: str | None = None
    federations: list[FederationOut] = []


class ConvocationOut(ORMModel):
    id: int
    player_id: int
    kind: str
    slot_order: int | None = None
    player: PlayerOut


class UnavailabilityOut(ORMModel):
    id: int
    player_id: int
    date: date
    reason: str | None = None
    player: PlayerOut


class MatchOut(ORMModel):
    id: int
    match_date: date
    match_time: time | None = None
    competition: str | None = None
    matchday: int | None = None
    home_score: int | None = None
    away_score: int | None = None
    notes: str | None = None
    published: bool
    federation: FederationOut
    home_team: TeamOut
    away_team: TeamOut
    venue: VenueOut | None = None
    has_convocations: bool = False
    has_unavailabilities: bool = False
    has_transport: bool = False


class TransportOut(ORMModel):
    id: int
    match_id: int
    kind: str
    driver_id: int | None = None
    driver: PlayerOut | None = None
    seats_total: int
    seats_available: int | None = None
    notes: str | None = None


class MatchDetailOut(MatchOut):
    convocations: list[ConvocationOut] = []
    unavailabilities: list[UnavailabilityOut] = []
    transport: list[TransportOut] = []


class LoginIn(BaseModel):
    password: str


class FederationIn(BaseModel):
    code: str
    name: str
    logo_url: str | None = None
    color: str | None = None


class TeamIn(BaseModel):
    name: str
    logo_url: str | None = None
    city: str | None = None
    is_ours: bool = False
    federation_ids: list[int] = []


class VenueIn(BaseModel):
    name: str
    address: str | None = None
    maps_url: str | None = None
    team_ids: list[int] = []


class PlayerIn(BaseModel):
    first_name: str
    last_name: str
    photo_url: str | None = None
    code_eisi: str | None = None
    code_csain: str | None = None
    role: int
    role2_type: str | None = None
    shot_distance_cm: int | None = None
    active: bool = True
    email: str | None = None
    phone: str | None = None
    federation_ids: list[int] = []


class MatchIn(BaseModel):
    match_date: date
    match_time: time | None = None
    federation_id: int
    home_team_id: int
    away_team_id: int
    venue_id: int | None = None
    competition: str | None = None
    matchday: int | None = None
    home_score: int | None = None
    away_score: int | None = None
    notes: str | None = None
    published: bool = False


class ConvocationItem(BaseModel):
    player_id: int
    kind: str = "starter"
    slot_order: int | None = None


class ConvocationsIn(BaseModel):
    items: list[ConvocationItem]


class UnavailabilityIn(BaseModel):
    player_id: int
    date: date
    reason: str | None = None


class SeasonIn(BaseModel):
    season_label: str | None = None
