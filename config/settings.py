from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_token: str

    # Tavily (web search)
    tavily_api_key: str

    # Gemini (AI analysis)
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_tokens: int = 4096

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
