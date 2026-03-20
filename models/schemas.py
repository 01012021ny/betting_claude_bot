"""Data models for the bot (simplified — web search based)."""

from __future__ import annotations

from pydantic import BaseModel


class MatchInfo(BaseModel):
    """Basic match info extracted from search results."""
    home: str
    away: str
    league: str = ""
    date: str = ""
