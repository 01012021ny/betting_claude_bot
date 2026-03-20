"""Handler for /next — auto-pick the best upcoming match and analyze it."""

from __future__ import annotations

import logging
import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards.inline import refresh_kb
from services.ai_analyzer import ai_analyzer
from services.web_search import web_search

logger = logging.getLogger(__name__)
router = Router()

MAX_TG_MESSAGE_LEN = 4096


async def _send_long_message(target, text: str, reply_markup=None) -> None:
    """Split and send long messages respecting Telegram's 4096 char limit."""
    if len(text) <= MAX_TG_MESSAGE_LEN:
        await target.answer(text, reply_markup=reply_markup)
        return

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


async def analyze_and_send(target, home: str, away: str) -> None:
    """Full pipeline: web search → AI analysis → send to user."""
    wait_msg = await target.answer(
        f"Анализирую матч: {home} — {away}\n\n"
        f"Ищу данные в интернете и генерирую AI-анализ..."
    )

    # Search for match data
    web_data = await web_search.search_match_data(home, away)

    if not web_data:
        await target.answer(
            "Не удалось найти данные по матчу. Попробуйте позже."
        )
        return

    # AI analysis
    analysis = await ai_analyzer.analyze_match(home, away, web_data)

    # Build a simple ID from team names for refresh
    match_id = f"{home}_vs_{away}"

    full_text = analysis
    await _send_long_message(
        target, full_text, reply_markup=refresh_kb(match_id)
    )


def _parse_match_line(text: str) -> tuple[str, str] | None:
    """Extract home and away team names from AI response."""
    # Pattern: "МАТЧ: Team1 — Team2"
    match = re.search(r"МАТЧ:\s*(.+?)\s*[—–-]\s*(.+)", text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None


@router.message(Command("next"))
async def cmd_next(message: Message) -> None:
    """Auto-pick the best upcoming match and analyze it."""
    await message.answer("Ищу лучший матч на сегодня...")

    # Search for today's matches
    web_data = await web_search.search_upcoming_matches()

    if not web_data:
        await message.answer("Не удалось найти матчи. Попробуйте позже.")
        return

    # Ask AI to pick the best match
    pick_result = await ai_analyzer.pick_best_match(web_data)

    parsed = _parse_match_line(pick_result)
    if not parsed:
        await message.answer(
            f"Не удалось определить матч из ответа AI.\n"
            f"Ответ: {pick_result[:200]}\n\n"
            f"Попробуйте /match <название команды>"
        )
        return

    home, away = parsed
    await analyze_and_send(message, home, away)


@router.callback_query(lambda c: c.data == "next_match")
async def cb_next_match(callback: CallbackQuery) -> None:
    """Callback version of /next."""
    await callback.answer()
    await cmd_next(callback.message)


@router.callback_query(lambda c: c.data and c.data.startswith("refresh_"))
async def cb_refresh(callback: CallbackQuery) -> None:
    """Refresh analysis for a match."""
    await callback.answer("Обновляю анализ...")
    match_id = callback.data[len("refresh_"):]

    parts = match_id.split("_vs_")
    if len(parts) != 2:
        await callback.message.answer("Не удалось определить матч для обновления.")
        return

    home, away = parts
    await analyze_and_send(callback.message, home, away)
