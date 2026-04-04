from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./starlight.db"
    redis_url: str = "redis://localhost/0"

    # LLM
    llm_model: str = "glm-4-flash"
    llm_api_key: str = ""
    llm_base_url: str = "https://open.bigmodel.cn/api/anthropic"

    # Cartridges
    cartridges_dir: str = "./cartridges"

    # Assessment
    assessment_max_turns: int = 3

    # Telegram
    bot_token: str = ""
    bot_mode: str = "polling"  # "polling" or "webhook"
    webhook_url: str = ""  # for webhook mode

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_prefix = "STARLIGHT_"


settings = Settings()
