from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_token: str

    # Tavily (web search)
    tavily_api_key: str = ""

    # Anthropic Claude (AI analysis)
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096

    # Legacy keys (not used, kept so pydantic doesn't reject them)
    gemini_api_key: str = ""
    api_football_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
