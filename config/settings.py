from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_token: str

    # Tavily (web search)
    tavily_api_key: str = ""

    # Gemini (AI analysis)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_tokens: int = 4096

    # Legacy keys (kept for backwards compat, not used)
    anthropic_api_key: str = ""
    api_football_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
