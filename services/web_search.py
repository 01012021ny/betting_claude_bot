"""Tavily web search client for sports data retrieval."""

from __future__ import annotations

import logging
from typing import Optional

import aiohttp

from config.settings import settings

logger = logging.getLogger(__name__)


class WebSearchClient:
    """Async client for Tavily Search API."""

    def __init__(self) -> None:
        self._api_key = settings.tavily_api_key
        self._base_url = "https://api.tavily.com"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def search(self, query: str, max_results: int = 5) -> str:
        """Search the web and return combined text results."""
        session = await self._get_session()

        payload = {
            "api_key": self._api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
        }

        try:
            async with session.post(
                f"{self._base_url}/search", json=payload
            ) as resp:
                if resp.status != 200:
                    logger.error("Tavily search returned %d", resp.status)
                    return ""
                data = await resp.json()
        except Exception:
            logger.exception("Tavily search failed")
            return ""

        # Build combined text from results
        parts: list[str] = []

        # Include Tavily's AI-generated answer if available
        answer = data.get("answer")
        if answer:
            parts.append(f"Краткий ответ: {answer}\n")

        for item in data.get("results", []):
            title = item.get("title", "")
            content = item.get("content", "")
            url = item.get("url", "")
            parts.append(f"[{title}]({url})\n{content}")

        return "\n\n".join(parts)

    async def search_match_data(self, home: str, away: str) -> str:
        """Search for comprehensive match data for analysis."""
        queries = [
            f"{home} vs {away} match preview lineup team news",
            f"{home} {away} head to head form statistics betting odds",
        ]

        all_results: list[str] = []
        for q in queries:
            result = await self.search(q, max_results=5)
            if result:
                all_results.append(result)

        return "\n\n---\n\n".join(all_results)

    async def search_upcoming_matches(self) -> str:
        """Search for today's top upcoming football matches."""
        result = await self.search(
            "top football matches today preview schedule kickoff time",
            max_results=8,
        )
        return result

    async def search_team_matches(self, team_name: str) -> str:
        """Search for upcoming matches for a specific team."""
        result = await self.search(
            f"{team_name} next match schedule date time opponent",
            max_results=5,
        )
        return result


# Singleton
web_search = WebSearchClient()
