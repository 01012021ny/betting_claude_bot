"""Handlers for /start and /help commands."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards.inline import main_menu_kb

router = Router()

WELCOME_TEXT = """\
Привет! Я — бот спортивной аналитики на базе AI.

Что я умею:
• Ищу актуальные данные о матчах в интернете
• Анализирую составы, форму, историю встреч
• Даю до 20 рекомендаций по ставкам с оценкой уверенности

Команды:
/next — анализ лучшего матча дня (авто-выбор)
/match <название> — поиск и анализ конкретного матча
/help — эта справка

Нажмите кнопку ниже или используйте команду."""

HELP_TEXT = """\
Доступные команды:

/next — бот ищет в интернете лучший матч дня \
и даёт полный анализ с рекомендациями

/match Real Madrid — поиск матчей с участием команды, \
выбор и анализ

Анализ включает:
1. Обзор матча
2. Составы и потери
3. Форма команд (последние матчи)
4. История личных встреч (H2H)
5. Тактический расклад
6. До 20 рекомендаций по ставкам (★★★/★★☆/★☆☆)
7. Лучшая ставка дня

Данные: веб-поиск (Tavily)
AI: Claude (Anthropic)"""


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
