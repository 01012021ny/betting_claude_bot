"""Handlers for /start and /help commands."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards.inline import main_menu_kb
from services.sports_api import get_api_usage

router = Router()

WELCOME_TEXT = """\
Привет! Я — бот спортивной аналитики на базе AI.

Что я умею:
• Автоматически нахожу ближайший значимый матч
• Анализирую составы, форму, историю встреч
• Даю до 20 рекомендаций по ставкам с оценкой уверенности

Команды:
/next — анализ ближайшего значимого матча (авто-выбор)
/match <название> — поиск и анализ конкретного матча
/status — статус API и лимиты
/help — эта справка

Нажмите кнопку ниже или используйте команду."""

HELP_TEXT = """\
Доступные команды:

/next — бот сам выбирает ближайший значимый матч \
(в течение 30 минут) и даёт полный анализ с рекомендациями

/match Реал Мадрид — поиск матчей с участием команды \
(сегодня и завтра), выбор и анализ

/status — текущий расход API-запросов

Как работает выбор матча:
Бот ранжирует матчи по значимости: Лига Чемпионов > \
Премьер-лига > Ла Лига > ... Дерби и плей-офф получают бонус.

Анализ включает:
1. Обзор матча
2. Составы и потери
3. Форма команд (последние 5 матчей)
4. История личных встреч (H2H)
5. Тактический расклад
6. До 20 рекомендаций по ставкам (★★★/★★☆/★☆☆)
7. Лучшая ставка дня"""


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
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
    await message.answer(text)
