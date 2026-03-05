"""Handler for /next — auto-pick the best upcoming match and analyze it."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import match_list_kb, refresh_kb
from models.schemas import MatchData
from services.ai_analyzer import ai_analyzer  # noqa: F401 — used in analyze_and_send
from services.match_selector import get_top_matches, select_best_match
from services.sports_api import sports_api

logger = logging.getLogger(__name__)
router = Router()

MAX_TG_MESSAGE_LEN = 4096


async def _send_long_message(target, text: str, reply_markup=None) -> None:
    """Split and send long messages respecting Telegram's 4096 char limit."""
    if len(text) <= MAX_TG_MESSAGE_LEN:
        await target.answer(text, reply_markup=reply_markup)
        return

    # Split by double newlines first, then by single newlines
    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        if len(current) + len(paragraph) + 2 > MAX_TG_MESSAGE_LEN:
            if current:
                chunks.append(current.strip())
            current = paragraph
        else:
            current = current + "\n\n" + paragraph if current else paragraph

    if current.strip():
        chunks.append(current.strip())

    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        await target.answer(chunk, reply_markup=reply_markup if is_last else None)


async def analyze_and_send(target, match) -> None:
    """Full pipeline: collect data → AI analysis → send to user."""
    # Notify user
    wait_msg = await target.answer(
        f"Анализирую матч: {match.home.name} — {match.away.name}\n"
        f"({match.league_name}, {match.date.strftime('%H:%M UTC')})\n\n"
        f"Собираю данные и генерирую AI-анализ..."
    )

    # Collect all match data in parallel
    lineups_task = asyncio.create_task(sports_api.get_lineups(match.fixture_id))
    h2h_task = asyncio.create_task(sports_api.get_h2h(match.home.id, match.away.id))
    home_form_task = asyncio.create_task(sports_api.get_team_form(match.home.id))
    away_form_task = asyncio.create_task(sports_api.get_team_form(match.away.id))
    injuries_task = asyncio.create_task(sports_api.get_injuries(match.fixture_id))

    lineups, h2h, home_form, away_form, injuries = await asyncio.gather(
        lineups_task, h2h_task, home_form_task, away_form_task, injuries_task
    )

    home_lineup = lineups[0] if len(lineups) > 0 else None
    away_lineup = lineups[1] if len(lineups) > 1 else None

    match_data = MatchData(
        match=match,
        home_form=home_form,
        away_form=away_form,
        h2h=h2h,
        injuries=injuries,
        home_lineup=home_lineup,
        away_lineup=away_lineup,
    )

    # AI analysis
    analysis = await ai_analyzer.analyze_match(match_data)

    # Send result
    header = (
        f"⚽ {match.home.name} — {match.away.name}\n"
        f"🏆 {match.league_name} | {match.league_round or ''}\n"
        f"📅 {match.date.strftime('%d.%m.%Y %H:%M UTC')}\n"
        f"🏟 {match.venue or 'N/A'}\n"
        f"{'─' * 30}\n\n"
    )

    full_text = header + analysis
    await _send_long_message(target, full_text, reply_markup=refresh_kb(match.fixture_id))


@router.message(Command("next"))
async def cmd_next(message: Message) -> None:
    """Auto-pick the best upcoming match and analyze it."""
    matches = await sports_api.get_upcoming_fixtures(minutes=30)

    if not matches:
        # Try wider window
        matches = await sports_api.get_upcoming_fixtures(minutes=120)
        if not matches:
            await message.answer(
                "Нет значимых матчей в ближайшие 2 часа.\n"
                "Используйте /match <название команды> для поиска конкретного матча."
            )
            return

        # Show list if no matches within 30 min
        top = get_top_matches(matches, n=5)
        await message.answer(
            "В ближайшие 30 минут нет матчей.\n"
            "Вот ближайшие значимые матчи (до 2 часов):",
            reply_markup=match_list_kb(top),
        )
        return

    best = select_best_match(matches)
    if not best:
        await message.answer("Не удалось выбрать матч. Попробуйте позже.")
        return

    await analyze_and_send(message, best)


@router.callback_query(lambda c: c.data == "next_match")
async def cb_next_match(callback: CallbackQuery) -> None:
    """Callback version of /next."""
    await callback.answer()
    matches = await sports_api.get_upcoming_fixtures(minutes=60)

    if not matches:
        await callback.message.answer("Нет матчей в ближайший час.")
        return

    best = select_best_match(matches)
    if best:
        await analyze_and_send(callback.message, best)


@router.callback_query(lambda c: c.data and c.data.startswith("analyze_"))
async def cb_analyze_match(callback: CallbackQuery) -> None:
    """Analyze a specific match from the list."""
    await callback.answer()
    fixture_id = int(callback.data.split("_")[1])

    # Find match in cache
    for minutes in (30, 60, 120):
        matches = await sports_api.get_upcoming_fixtures(minutes=minutes)
        for m in matches:
            if m.fixture_id == fixture_id:
                await analyze_and_send(callback.message, m)
                return

    await callback.message.answer("Матч не найден. Попробуйте /next.")


@router.callback_query(lambda c: c.data and c.data.startswith("refresh_"))
async def cb_refresh(callback: CallbackQuery) -> None:
    """Refresh analysis for a match."""
    await callback.answer("Обновляю анализ...")
    fixture_id = int(callback.data.split("_")[1])

    for minutes in (30, 60, 120, 360):
        matches = await sports_api.get_upcoming_fixtures(minutes=minutes)
        for m in matches:
            if m.fixture_id == fixture_id:
                await analyze_and_send(callback.message, m)
                return

    await callback.message.answer("Матч не найден или уже завершился.")


@router.callback_query(lambda c: c.data == "api_status")
async def cb_api_status(callback: CallbackQuery) -> None:
    """Show API usage status."""
    await callback.answer()
    from services.sports_api import get_api_usage

    used, limit = get_api_usage()
    remaining = limit - used
    bar_len = 20
    filled = int(bar_len * used / limit) if limit else 0
    bar = "█" * filled + "░" * (bar_len - filled)

    text = (
        f"📊 Статус API-Football\n\n"
        f"Использовано: {used}/{limit}\n"
        f"Осталось: {remaining}\n"
        f"[{bar}] {used * 100 // limit}%"
    )
    await callback.message.answer(text)
