"""Handler for /match <query> — search and analyze a specific match."""

from __future__ import annotations

import logging
import re

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.handlers.auto_pick import analyze_and_send
from bot.keyboards.inline import match_list_kb
from services.ai_analyzer import ai_analyzer
from services.web_search import web_search

logger = logging.getLogger(__name__)
router = Router()


def _parse_match_list(text: str) -> list[tuple[str, str, str]]:
    """Parse match list from AI response.

    Returns list of (home, away, info) tuples.
    """
    matches = []
    for line in text.strip().split("\n"):
        line = line.strip().lstrip("•").strip()
        if not line or "НЕТ МАТЧЕЙ" in line:
            continue
        # Pattern: "Team1 — Team2 | League | Date"
        m = re.match(r"(.+?)\s*[—–-]\s*(.+?)\s*\|\s*(.+)", line)
        if m:
            home = m.group(1).strip()
            away = m.group(2).strip()
            info = m.group(3).strip()
            matches.append((home, away, info))
    return matches


@router.message(Command("match"))
async def cmd_match(message: Message, command: CommandObject) -> None:
    """Search for a match by team name and analyze it."""
    query = command.args
    if not query:
        await message.answer(
            "Укажите название команды после команды.\n"
            "Пример: /match Реал Мадрид"
        )
        return

    await message.answer(f"Ищу матчи с участием '{query}'...")

    # Search for team's matches
    web_data = await web_search.search_team_matches(query)

    if not web_data:
        await message.answer(
            f"Не удалось найти матчи с '{query}'.\n"
            "Попробуйте другое название (на английском).\n"
            "Пример: /match Real Madrid"
        )
        return

    # Ask AI to extract match list
    match_list_text = await ai_analyzer.find_team_matches(web_data)

    matches = _parse_match_list(match_list_text)

    if not matches:
        # Try to analyze directly — maybe there's only one obvious match
        await message.answer(
            f"Не удалось распознать список матчей.\n"
            f"Попробую проанализировать ближайший матч '{query}'..."
        )
        # Use query as team name and search for data directly
        web_data_full = await web_search.search_match_data(query, "")
        if web_data_full:
            analysis = await ai_analyzer.analyze_match(query, "opponent", web_data_full)
            await message.answer(analysis[:4096])
        return

    if len(matches) == 1:
        home, away, _info = matches[0]
        await analyze_and_send(message, home, away)
        return

    # Multiple matches — show list
    await message.answer(
        f"Найдено {len(matches)} матчей. Выберите:",
        reply_markup=match_list_kb(matches[:5]),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("analyze_"))
async def cb_analyze_match(callback: CallbackQuery) -> None:
    """Analyze a specific match from the list."""
    await callback.answer()
    match_id = callback.data[len("analyze_"):]

    parts = match_id.split("_vs_")
    if len(parts) != 2:
        await callback.message.answer("Ошибка: не удалось определить матч.")
        return

    home, away = parts
    await analyze_and_send(callback.message, home, away)
