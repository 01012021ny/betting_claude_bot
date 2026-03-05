"""Handler for /match <query> — search and analyze a specific match."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.handlers.auto_pick import analyze_and_send
from bot.keyboards.inline import match_list_kb
from services.match_selector import get_top_matches
from services.sports_api import sports_api

logger = logging.getLogger(__name__)
router = Router()


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

    matches = await sports_api.search_fixtures(query)

    if not matches:
        await message.answer(
            f"Матчи с '{query}' не найдены (сегодня и завтра).\n"
            "Попробуйте другое название (на английском).\n"
            "Пример: /match Real Madrid"
        )
        return

    if len(matches) == 1:
        # Single match found — analyze directly
        await analyze_and_send(message, matches[0])
        return

    # Multiple matches — show list
    top = get_top_matches(matches, n=5)
    await message.answer(
        f"Найдено {len(matches)} матчей. Выберите:",
        reply_markup=match_list_kb(top),
    )
