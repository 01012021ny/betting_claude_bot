"""Algorithm to select the most significant upcoming match."""

from __future__ import annotations

from models.schemas import Match

# League significance weights (higher = more important)
LEAGUE_WEIGHTS: dict[str, int] = {
    # International tournaments
    "World Cup": 120,
    "Euro Championship": 115,
    "Copa America": 110,
    "Africa Cup of Nations": 105,
    # Club European competitions
    "UEFA Champions League": 110,
    "Champions League": 110,
    "UEFA Europa League": 85,
    "Europa League": 85,
    "UEFA Europa Conference League": 70,
    "Conference League": 70,
    "UEFA Super Cup": 80,
    # Top-5 leagues
    "Premier League": 100,
    "La Liga": 95,
    "Serie A": 92,
    "Bundesliga": 90,
    "Ligue 1": 87,
    # Top-5 cups
    "FA Cup": 78,
    "Copa del Rey": 78,
    "Coppa Italia": 75,
    "DFB Pokal": 75,
    "Coupe de France": 72,
    # Second tier leagues
    "Primeira Liga": 68,
    "Eredivisie": 66,
    "Premier League": 100,  # Russia RPL
    "Russian Premier League": 70,
    "Liga Profesional": 65,
    "Brasileirão": 70,
    "Serie A": 92,  # Brazil Serie A same weight
    "MLS": 55,
    "Super Lig": 60,
    # International qualifiers
    "Nations League": 78,
    "World Cup - Qualification": 82,
    "Euro - Qualification": 80,
    # Other
    "Championship": 55,
    "Liga MX": 50,
    "J1 League": 45,
    "K League 1": 45,
    "A-League": 45,
    "Saudi Pro League": 55,
}

# Well-known derby matchups (team name substrings)
DERBIES: list[tuple[str, str]] = [
    ("Real Madrid", "Barcelona"),
    ("Real Madrid", "Atletico"),
    ("Barcelona", "Atletico"),
    ("Manchester United", "Manchester City"),
    ("Manchester United", "Liverpool"),
    ("Liverpool", "Everton"),
    ("Arsenal", "Tottenham"),
    ("Chelsea", "Arsenal"),
    ("AC Milan", "Inter"),
    ("Juventus", "Inter"),
    ("Roma", "Lazio"),
    ("Napoli", "Juventus"),
    ("Bayern", "Dortmund"),
    ("PSG", "Marseille"),
    ("Porto", "Benfica"),
    ("Porto", "Sporting"),
    ("Benfica", "Sporting"),
    ("Galatasaray", "Fenerbahce"),
    ("Boca Juniors", "River Plate"),
    ("Flamengo", "Fluminense"),
    ("CSKA", "Spartak"),
    ("Zenit", "Spartak"),
    ("Celtic", "Rangers"),
    ("Ajax", "Feyenoord"),
    ("Ajax", "PSV"),
]


def _is_derby(home: str, away: str) -> bool:
    for t1, t2 in DERBIES:
        if (t1.lower() in home.lower() and t2.lower() in away.lower()) or (
            t2.lower() in home.lower() and t1.lower() in away.lower()
        ):
            return True
    return False


def _is_knockout(round_name: str | None) -> bool:
    if not round_name:
        return False
    kw = round_name.lower()
    return any(
        term in kw
        for term in [
            "final",
            "semi",
            "quarter",
            "1/2",
            "1/4",
            "1/8",
            "knockout",
            "round of",
            "play-off",
            "playoff",
        ]
    )


def score_match(match: Match) -> int:
    """Calculate significance score for a match."""
    # Base score from league weight
    score = LEAGUE_WEIGHTS.get(match.league_name, 30)

    # Derby bonus
    if _is_derby(match.home.name, match.away.name):
        score += 20

    # Knockout / cup stage bonus
    if _is_knockout(match.league_round):
        score += 15

    return score


def select_best_match(matches: list[Match]) -> Match | None:
    """Select the most significant match from a list."""
    if not matches:
        return None

    scored = [(score_match(m), m) for m in matches]
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_match = scored[0]
    return best_match


def get_top_matches(matches: list[Match], n: int = 5) -> list[tuple[int, Match]]:
    """Get top N most significant matches with their scores."""
    scored = [(score_match(m), m) for m in matches]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:n]
