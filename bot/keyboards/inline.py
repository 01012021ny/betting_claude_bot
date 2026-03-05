"""Inline keyboards for the bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from models.schemas import Match


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ближайший матч", callback_data="next_match")],
            [InlineKeyboardButton(text="Статус API", callback_data="api_status")],
        ]
    )


def match_list_kb(matches: list[tuple[int, Match]]) -> InlineKeyboardMarkup:
    """Keyboard with list of matches (score, match)."""
    buttons = []
    for _score, match in matches[:5]:
        label = f"{match.home.name} — {match.away.name} ({match.league_name})"
        buttons.append(
            [InlineKeyboardButton(
                text=label,
                callback_data=f"analyze_{match.fixture_id}",
            )]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def refresh_kb(fixture_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Обновить анализ",
                    callback_data=f"refresh_{fixture_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Другой матч",
                    callback_data="next_match",
                ),
            ],
        ]
    )
