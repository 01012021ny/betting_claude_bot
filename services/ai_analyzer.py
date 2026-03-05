"""Claude API integration for match analysis."""

from __future__ import annotations

import logging

import anthropic

from config.settings import settings
from models.schemas import MatchData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Ты — профессиональный спортивный аналитик с 15-летним опытом.
Анализируй матчи объективно, без эмоций. Всегда указывай риски.
Отвечай на русском языке. Формат ответа строго по шаблону.
Не придумывай данные — используй только то, что предоставлено.
Если данных недостаточно, укажи это явно."""

ANALYSIS_TEMPLATE = """\
Проанализируй матч {home} — {away}.
Лига: {league} ({country}), Раунд: {round}
Дата и время: {date}
Стадион: {venue}

{lineups_section}

{injuries_section}

{home_form_section}

{away_form_section}

{h2h_section}

Дай анализ строго по следующему шаблону:

1. ОБЗОР МАТЧА
Контекст и значимость матча (2-3 предложения).

2. СОСТАВЫ И ПОТЕРИ
Ключевые отсутствующие игроки и их влияние на игру.

3. ФОРМА КОМАНД
Тренды, серии, домашняя/выездная статистика.

4. ИСТОРИЯ ВСТРЕЧ
Паттерны в личных встречах.

5. ТАКТИЧЕСКИЙ РАСКЛАД
Ожидаемый стиль игры обеих команд.

6. РЕКОМЕНДАЦИИ ПО СТАВКАМ (до 20 вариантов)

Для каждой ставки используй формат:
• [Тип ставки] — КФ ~X.XX — [★☆☆/★★☆/★★★] — Обоснование в 1 предложение

Уровни уверенности:
★★★ — высокая (>70%)
★★☆ — средняя (50-70%)
★☆☆ — низкая (<50%)

Сортируй по уверенности (сначала ★★★).

7. ВЕРДИКТ
Общий вывод и лучшая ставка дня (одна, самая обоснованная)."""


def _format_lineups(data: MatchData) -> str:
    parts = []
    for lineup in [data.home_lineup, data.away_lineup]:
        if not lineup:
            continue
        xi_names = [p.name for p in lineup.start_xi]
        subs_names = [p.name for p in lineup.substitutes[:5]]
        section = f"**{lineup.team}** (схема: {lineup.formation or '?'})"
        if lineup.coach:
            section += f"\nТренер: {lineup.coach}"
        section += f"\nОсновной состав: {', '.join(xi_names) if xi_names else 'нет данных'}"
        if subs_names:
            section += f"\nЗапасные: {', '.join(subs_names)}"
        parts.append(section)

    if not parts:
        return "СОСТАВЫ:\nДанные о составах пока недоступны."
    return "СОСТАВЫ:\n" + "\n\n".join(parts)


def _format_injuries(data: MatchData) -> str:
    if not data.injuries:
        return "ТРАВМЫ И ДИСКВАЛИФИКАЦИИ:\nДанные недоступны."

    lines = []
    for inj in data.injuries:
        lines.append(f"• {inj.player_name} ({inj.team}) — {inj.type}: {inj.reason}")
    return "ТРАВМЫ И ДИСКВАЛИФИКАЦИИ:\n" + "\n".join(lines)


def _format_form(data: MatchData, is_home: bool) -> str:
    form = data.home_form if is_home else data.away_form
    label = "ФОРМА ХОЗЯЕВ" if is_home else "ФОРМА ГОСТЕЙ"

    if not form or not form.last_matches:
        team_name = data.match.home.name if is_home else data.match.away.name
        return f"{label} ({team_name}):\nДанные недоступны."

    results = "".join(m.result for m in form.last_matches)
    lines = [
        f"{label} ({form.team.name}): {results} "
        f"({form.wins}W-{form.draws}D-{form.losses}L, "
        f"голы {form.goals_for}:{form.goals_against})"
    ]
    for m in form.last_matches:
        lines.append(
            f"  {'🏠' if m.home_away == 'H' else '✈️'} vs {m.opponent}: "
            f"{m.score} ({m.result}) — {m.league}"
        )
    return "\n".join(lines)


def _format_h2h(data: MatchData) -> str:
    h2h = data.h2h
    if not h2h or h2h.total_matches == 0:
        return "ИСТОРИЯ ВСТРЕЧ (H2H):\nДанные недоступны."

    lines = [
        f"ИСТОРИЯ ВСТРЕЧ (H2H): {h2h.total_matches} матчей — "
        f"победы хозяев: {h2h.home_wins}, ничьих: {h2h.draws}, "
        f"победы гостей: {h2h.away_wins}"
    ]
    for m in h2h.recent_matches:
        lines.append(f"  {m.date}: {m.home_team} {m.score} {m.away_team} ({m.league})")
    return "\n".join(lines)


def _build_prompt(data: MatchData) -> str:
    return ANALYSIS_TEMPLATE.format(
        home=data.match.home.name,
        away=data.match.away.name,
        league=data.match.league_name,
        country=data.match.league_country,
        round=data.match.league_round or "—",
        date=data.match.date.strftime("%d.%m.%Y %H:%M UTC"),
        venue=data.match.venue or "неизвестно",
        lineups_section=_format_lineups(data),
        injuries_section=_format_injuries(data),
        home_form_section=_format_form(data, is_home=True),
        away_form_section=_format_form(data, is_home=False),
        h2h_section=_format_h2h(data),
    )


class AIAnalyzer:
    """Match analysis via Claude API."""

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def analyze_match(self, data: MatchData) -> str:
        """Generate full match analysis with betting recommendations."""
        prompt = _build_prompt(data)
        logger.info(
            "Sending analysis request to Claude for %s vs %s",
            data.match.home.name,
            data.match.away.name,
        )

        try:
            # anthropic SDK is sync; run in thread for async context
            import asyncio

            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: self._client.messages.create(
                    model=settings.claude_model,
                    max_tokens=settings.claude_max_tokens,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                ),
            )

            text = message.content[0].text
            return text

        except anthropic.APIError as e:
            logger.error("Claude API error: %s", e)
            return f"Ошибка AI-анализа: {e.message}"
        except Exception:
            logger.exception("Unexpected error during AI analysis")
            return "Произошла ошибка при генерации анализа. Попробуйте позже."


# Singleton
ai_analyzer = AIAnalyzer()
