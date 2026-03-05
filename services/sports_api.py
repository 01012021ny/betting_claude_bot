"""API-Football client with in-memory TTL cache."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import aiohttp

from config.settings import settings
from models.schemas import (
    FormMatch,
    H2HMatch,
    H2HRecord,
    LineupPlayer,
    Match,
    PlayerInjury,
    Team,
    TeamForm,
    TeamLineup,
)

logger = logging.getLogger(__name__)


class _Cache:
    """Simple in-memory cache with TTL."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (time.time() + ttl, value)

    def clear(self) -> None:
        self._store.clear()


cache = _Cache()

# Track daily API usage
_api_calls_today: dict[str, int] = {"date": "", "count": 0}
API_DAILY_LIMIT = 95  # leave 5 requests margin


def _check_rate_limit() -> bool:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _api_calls_today["date"] != today:
        _api_calls_today["date"] = today
        _api_calls_today["count"] = 0
    return _api_calls_today["count"] < API_DAILY_LIMIT


def _increment_usage() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _api_calls_today["date"] != today:
        _api_calls_today["date"] = today
        _api_calls_today["count"] = 0
    _api_calls_today["count"] += 1
    logger.info("API-Football usage: %d/%d", _api_calls_today["count"], API_DAILY_LIMIT)


def get_api_usage() -> tuple[int, int]:
    """Return (used, limit)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _api_calls_today["date"] != today:
        return 0, API_DAILY_LIMIT
    return _api_calls_today["count"], API_DAILY_LIMIT


class SportsAPIClient:
    """Async client for API-Football (api-sports.io)."""

    def __init__(self) -> None:
        self._base_url = settings.api_football_base_url
        self._headers = {
            "x-apisports-key": settings.api_football_key,
        }
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=15),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, endpoint: str, params: dict | None = None) -> dict | None:
        if not _check_rate_limit():
            logger.warning("API-Football daily limit reached!")
            return None

        session = await self._get_session()
        url = f"{self._base_url}/{endpoint}"
        try:
            async with session.get(url, params=params) as resp:
                _increment_usage()
                if resp.status != 200:
                    logger.error("API-Football %s returned %d", endpoint, resp.status)
                    return None
                data = await resp.json()
                if data.get("errors"):
                    logger.error("API-Football errors: %s", data["errors"])
                    return None
                return data
        except Exception:
            logger.exception("API-Football request failed: %s", endpoint)
            return None

    # ── Fixtures ──────────────────────────────────────────────

    async def get_upcoming_fixtures(self, minutes: int = 30) -> list[Match]:
        """Get fixtures starting within the next `minutes` minutes."""
        cache_key = f"upcoming_{minutes}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        data = await self._request("fixtures", {"date": date_str, "status": "NS"})
        if not data:
            return []

        matches: list[Match] = []
        for item in data.get("response", []):
            fixture = item["fixture"]
            league = item["league"]
            teams = item["teams"]

            match_time = datetime.fromisoformat(
                fixture["date"].replace("Z", "+00:00")
            )
            diff = (match_time - now).total_seconds()
            if 0 <= diff <= minutes * 60:
                matches.append(
                    Match(
                        fixture_id=fixture["id"],
                        league_id=league["id"],
                        league_name=league["name"],
                        league_country=league.get("country", ""),
                        league_round=league.get("round"),
                        home=Team(
                            id=teams["home"]["id"],
                            name=teams["home"]["name"],
                            logo=teams["home"].get("logo"),
                        ),
                        away=Team(
                            id=teams["away"]["id"],
                            name=teams["away"]["name"],
                            logo=teams["away"].get("logo"),
                        ),
                        date=match_time,
                        venue=fixture.get("venue", {}).get("name"),
                        status=fixture.get("status", {}).get("short", "NS"),
                    )
                )

        cache.set(cache_key, matches, settings.cache_ttl_fixtures)
        return matches

    async def search_fixtures(self, query: str) -> list[Match]:
        """Search today's and tomorrow's fixtures by team name."""
        now = datetime.now(timezone.utc)
        dates = [now.strftime("%Y-%m-%d"), (now + timedelta(days=1)).strftime("%Y-%m-%d")]
        query_lower = query.lower()

        all_matches: list[Match] = []
        for date_str in dates:
            cache_key = f"fixtures_{date_str}"
            cached = cache.get(cache_key)
            if cached is None:
                data = await self._request("fixtures", {"date": date_str})
                if not data:
                    continue
                cached = data.get("response", [])
                cache.set(cache_key, cached, settings.cache_ttl_fixtures)

            for item in cached:
                fixture = item["fixture"]
                league = item["league"]
                teams = item["teams"]
                home_name = teams["home"]["name"].lower()
                away_name = teams["away"]["name"].lower()

                if query_lower in home_name or query_lower in away_name:
                    match_time = datetime.fromisoformat(
                        fixture["date"].replace("Z", "+00:00")
                    )
                    all_matches.append(
                        Match(
                            fixture_id=fixture["id"],
                            league_id=league["id"],
                            league_name=league["name"],
                            league_country=league.get("country", ""),
                            league_round=league.get("round"),
                            home=Team(
                                id=teams["home"]["id"],
                                name=teams["home"]["name"],
                                logo=teams["home"].get("logo"),
                            ),
                            away=Team(
                                id=teams["away"]["id"],
                                name=teams["away"]["name"],
                                logo=teams["away"].get("logo"),
                            ),
                            date=match_time,
                            venue=fixture.get("venue", {}).get("name"),
                            status=fixture.get("status", {}).get("short"),
                        )
                    )

        return all_matches

    # ── Lineups ───────────────────────────────────────────────

    async def get_lineups(self, fixture_id: int) -> list[TeamLineup]:
        cache_key = f"lineups_{fixture_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._request("fixtures/lineups", {"fixture": fixture_id})
        if not data:
            return []

        lineups: list[TeamLineup] = []
        for item in data.get("response", []):
            team_name = item["team"]["name"]
            formation = item.get("formation")
            coach = item.get("coach", {}).get("name")

            start_xi = [
                LineupPlayer(
                    name=p["player"]["name"],
                    number=p["player"].get("number"),
                    position=p["player"].get("pos"),
                )
                for p in item.get("startXI", [])
            ]
            subs = [
                LineupPlayer(
                    name=p["player"]["name"],
                    number=p["player"].get("number"),
                    position=p["player"].get("pos"),
                )
                for p in item.get("substitutes", [])
            ]

            lineups.append(
                TeamLineup(
                    team=team_name,
                    formation=formation,
                    start_xi=start_xi,
                    substitutes=subs,
                    coach=coach,
                )
            )

        cache.set(cache_key, lineups, settings.cache_ttl_lineup)
        return lineups

    # ── H2H ───────────────────────────────────────────────────

    async def get_h2h(self, team1_id: int, team2_id: int) -> H2HRecord:
        cache_key = f"h2h_{min(team1_id, team2_id)}_{max(team1_id, team2_id)}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._request(
            "fixtures/headtohead",
            {"h2h": f"{team1_id}-{team2_id}", "last": 10},
        )
        if not data:
            return H2HRecord()

        response = data.get("response", [])
        home_wins = 0
        away_wins = 0
        draws = 0
        recent: list[H2HMatch] = []

        for item in response:
            teams = item["teams"]
            goals = item["goals"]
            fixture = item["fixture"]
            league = item.get("league", {})

            h_goals = goals["home"] or 0
            a_goals = goals["away"] or 0
            if h_goals > a_goals:
                home_wins += 1
            elif a_goals > h_goals:
                away_wins += 1
            else:
                draws += 1

            match_date = fixture.get("date", "")[:10]
            recent.append(
                H2HMatch(
                    date=match_date,
                    home_team=teams["home"]["name"],
                    away_team=teams["away"]["name"],
                    score=f"{h_goals}:{a_goals}",
                    league=league.get("name", ""),
                )
            )

        record = H2HRecord(
            total_matches=len(response),
            home_wins=home_wins,
            away_wins=away_wins,
            draws=draws,
            recent_matches=recent,
        )
        cache.set(cache_key, record, settings.cache_ttl_h2h)
        return record

    # ── Team Form ─────────────────────────────────────────────

    async def get_team_form(self, team_id: int, last_n: int = 5) -> TeamForm:
        cache_key = f"form_{team_id}_{last_n}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._request(
            "fixtures",
            {"team": team_id, "last": last_n, "status": "FT"},
        )
        if not data:
            return TeamForm(team=Team(id=team_id, name="Unknown"))

        response = data.get("response", [])
        team_name = ""
        wins = draws = losses = gf = ga = 0
        matches: list[FormMatch] = []

        for item in response:
            teams = item["teams"]
            goals = item["goals"]
            fixture = item["fixture"]
            league = item.get("league", {})

            is_home = teams["home"]["id"] == team_id
            if not team_name:
                team_name = teams["home"]["name"] if is_home else teams["away"]["name"]

            own_goals = (goals["home"] if is_home else goals["away"]) or 0
            opp_goals = (goals["away"] if is_home else goals["home"]) or 0
            opponent = teams["away"]["name"] if is_home else teams["home"]["name"]

            gf += own_goals
            ga += opp_goals

            if own_goals > opp_goals:
                result = "W"
                wins += 1
            elif own_goals < opp_goals:
                result = "L"
                losses += 1
            else:
                result = "D"
                draws += 1

            match_date = fixture.get("date", "")[:10]
            matches.append(
                FormMatch(
                    opponent=opponent,
                    result=result,
                    score=f"{own_goals}:{opp_goals}",
                    date=match_date,
                    home_away="H" if is_home else "A",
                    league=league.get("name", ""),
                )
            )

        form = TeamForm(
            team=Team(id=team_id, name=team_name or "Unknown"),
            last_matches=matches,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_for=gf,
            goals_against=ga,
        )
        cache.set(cache_key, form, settings.cache_ttl_form)
        return form

    # ── Injuries ──────────────────────────────────────────────

    async def get_injuries(self, fixture_id: int) -> list[PlayerInjury]:
        cache_key = f"injuries_{fixture_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        data = await self._request("injuries", {"fixture": fixture_id})
        if not data:
            return []

        injuries: list[PlayerInjury] = []
        for item in data.get("response", []):
            player = item.get("player", {})
            team = item.get("team", {})
            injuries.append(
                PlayerInjury(
                    player_name=player.get("name", "Unknown"),
                    team=team.get("name", "Unknown"),
                    type=player.get("type", "Unknown"),
                    reason=player.get("reason", ""),
                )
            )

        cache.set(cache_key, injuries, settings.cache_ttl_injuries)
        return injuries


# Singleton
sports_api = SportsAPIClient()
