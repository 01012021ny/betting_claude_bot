"""Anthropic Claude integration for match analysis."""

from __future__ import annotations

import logging

import anthropic

from config.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
Ты — профессиональный спортивный аналитик с 15-летним опытом.
Анализируй матчи объективно, без эмоций. Всегда указывай риски.
Отвечай на русском языке. Формат ответа строго по шаблону.

ВАЖНО: Всегда давай максимально полный анализ на основе доступных данных.
Используй свои знания о командах, лигах, тренерах и игроках.
Если по какому-то пункту мало информации — дай анализ на основе \
того, что знаешь, но укажи степень уверенности.
НИКОГДА не отказывайся от анализа. Всегда давай рекомендации."""

ANALYSIS_TEMPLATE = """\
Проанализируй матч: {home} — {away}

Вот актуальные данные из интернета:

{web_data}

Дай анализ строго по следующему шаблону:

# АНАЛИЗ МАТЧА: {home} — {away}

## 1. ОБЗОР МАТЧА
Контекст и значимость матча (2-3 предложения).

## 2. СОСТАВЫ И ПОТЕРИ
Ключевые отсутствующие игроки и их влияние на игру.

## 3. ФОРМА КОМАНД
Тренды, серии, домашняя/выездная статистика.

## 4. ИСТОРИЯ ВСТРЕЧ
Паттерны в личных встречах.

## 5. ТАКТИЧЕСКИЙ РАСКЛАД
Ожидаемый стиль игры обеих команд.

## 6. РЕКОМЕНДАЦИИ ПО СТАВКАМ (до 20 вариантов)

Для каждой ставки используй формат:
• [Тип ставки] — КФ ~X.XX — [★☆☆/★★☆/★★★] — Обоснование в 1 предложение

Уровни уверенности:
★★★ — высокая (>70%)
★★☆ — средняя (50-70%)
★☆☆ — низкая (<50%)

Сортируй по уверенности (сначала ★★★).

## 7. ВЕРДИКТ
Общий вывод и лучшая ставка дня (одна, самая обоснованная)."""

PICK_MATCH_TEMPLATE = """\
Вот информация о сегодняшних футбольных матчах:

{web_data}

Выбери один самый значимый и интересный матч для ставок из списка.
Приоритеты: Лига Чемпионов > Топ-5 лиг > Дерби > Плей-офф.

Ответь СТРОГО в формате:
МАТЧ: <Команда 1> — <Команда 2>

Только одна строка, ничего больше."""

FIND_MATCHES_TEMPLATE = """\
Вот информация о матчах с участием запрошенной команды:

{web_data}

Выведи список найденных ближайших матчей.
Ответь СТРОГО в формате (один матч на строку):
• <Команда 1> — <Команда 2> | <Лига> | <Дата и время>

Если матчей нет — ответь: НЕТ МАТЧЕЙ"""


class AIAnalyzer:
    """Match analysis via Anthropic Claude API."""

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def _generate(self, prompt: str, system: str = SYSTEM_PROMPT) -> str:
        """Send request to Claude and return text response."""
        try:
            message = await self._client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.claude_max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text

        except Exception as e:
            logger.exception("Claude API error")
            return f"Ошибка AI-анализа: {e}"

    async def analyze_match(self, home: str, away: str, web_data: str) -> str:
        """Generate full match analysis with betting recommendations."""
        prompt = ANALYSIS_TEMPLATE.format(
            home=home, away=away, web_data=web_data
        )
        logger.info("Sending analysis request to Claude for %s vs %s", home, away)
        return await self._generate(prompt)

    async def pick_best_match(self, web_data: str) -> str:
        """Ask AI to pick the best match from search results."""
        prompt = PICK_MATCH_TEMPLATE.format(web_data=web_data)
        return await self._generate(
            prompt,
            system="Ты — спортивный эксперт. Отвечай кратко и точно.",
        )

    async def find_team_matches(self, web_data: str) -> str:
        """Extract match list from search results."""
        prompt = FIND_MATCHES_TEMPLATE.format(web_data=web_data)
        return await self._generate(
            prompt,
            system="Ты — спортивный эксперт. Отвечай кратко и точно.",
        )


# Singleton
ai_analyzer = AIAnalyzer()
