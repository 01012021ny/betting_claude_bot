from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_token: str

    # Anthropic (Claude)
    anthropic_api_key: str

    # API-Football (api-sports.io)
    api_football_key: str
    api_football_base_url: str = "https://v3.football.api-sports.io"

    # Cache TTLs (seconds)
    cache_ttl_fixtures: int = 600  # 10 min — upcoming fixtures list
    cache_ttl_lineup: int = 3600  # 1 hour — lineups (set once before match)
    cache_ttl_h2h: int = 2_592_000  # 30 days — H2H history rarely changes
    cache_ttl_form: int = 86_400  # 24 hours — team recent form
    cache_ttl_injuries: int = 21_600  # 6 hours — injury list

    # Match selector
    upcoming_window_minutes: int = 30

    # Claude
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
