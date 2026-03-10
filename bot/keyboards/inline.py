"""Inline keyboards for the bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ближайший матч", callback_data="next_match")],
        ]
    )


def match_list_kb(matches: list[tuple[str, str, str]]) -> InlineKeyboardMarkup:
    """Keyboard with list of matches (home, away, info)."""
    buttons = []
    for home, away, info in matches[:5]:
        label = f"{home} — {away} ({info[:30]})"
        match_id = f"{home}_vs_{away}"
        buttons.append(
            [InlineKeyboardButton(
                text=label[:60],
                callback_data=f"analyze_{match_id}"[:64],
            )]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def refresh_kb(match_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Обновить анализ",
                    callback_data=f"refresh_{match_id}"[:64],
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
