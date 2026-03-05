from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Team(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None
    country: Optional[str] = None


class Match(BaseModel):
    fixture_id: int
    league_id: int
    league_name: str
    league_country: str
    league_round: Optional[str] = None
    home: Team
    away: Team
    date: datetime
    venue: Optional[str] = None
    status: Optional[str] = None  # NS, 1H, HT, 2H, FT, etc.
    score_home: Optional[int] = None
    score_away: Optional[int] = None


class TeamForm(BaseModel):
    team: Team
    last_matches: list[FormMatch] = []
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0


class FormMatch(BaseModel):
    opponent: str
    result: str  # W, D, L
    score: str  # "2:1"
    date: str
    home_away: str  # H or A
    league: str = ""


# Forward ref resolution
TeamForm.model_rebuild()


class PlayerInjury(BaseModel):
    player_name: str
    team: str
    type: str  # Injury, Suspension, etc.
    reason: str = ""


class H2HRecord(BaseModel):
    total_matches: int = 0
    home_wins: int = 0
    away_wins: int = 0
    draws: int = 0
    recent_matches: list[H2HMatch] = []


class H2HMatch(BaseModel):
    date: str
    home_team: str
    away_team: str
    score: str  # "2:1"
    league: str = ""


class LineupPlayer(BaseModel):
    name: str
    number: Optional[int] = None
    position: Optional[str] = None


class TeamLineup(BaseModel):
    team: str
    formation: Optional[str] = None
    start_xi: list[LineupPlayer] = []
    substitutes: list[LineupPlayer] = []
    coach: Optional[str] = None


class MatchData(BaseModel):
    """All collected data for a match, passed to AI analyzer."""
    match: Match
    home_form: Optional[TeamForm] = None
    away_form: Optional[TeamForm] = None
    h2h: Optional[H2HRecord] = None
    injuries: list[PlayerInjury] = []
    home_lineup: Optional[TeamLineup] = None
    away_lineup: Optional[TeamLineup] = None
