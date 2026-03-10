"""Entry point for the Telegram betting analytics bot."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from bot.handlers import auto_pick, match, start
from config.settings import settings
from services.web_search import web_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    logger.info("Bot started. Username: %s", (await bot.me()).username)


async def on_shutdown(bot: Bot) -> None:
    logger.info("Shutting down...")
    await web_search.close()


async def main() -> None:
    missing = []
    if not settings.tavily_api_key:
        missing.append("TAVILY_API_KEY")
    if not settings.anthropic_api_key:
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        logger.warning(
            "Missing keys in .env: %s — bot will start but analysis won't work. "
            "Add them to your .env file.", ", ".join(missing),
        )

    bot = Bot(
        token=settings.telegram_token,
        default=DefaultBotProperties(parse_mode=None),
    )

    dp = Dispatcher()

    # Register routers
    dp.include_router(start.router)
    dp.include_router(auto_pick.router)
    dp.include_router(match.router)

    # Lifecycle hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
