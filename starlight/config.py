from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./starlight.db"
    redis_url: str = "redis://localhost/0"
    llm_model: str = "glm-4-flash"
    llm_api_key: str = ""
    llm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    cartridges_dir: str = "./cartridges"
    assessment_max_turns: int = 3

    class Config:
        env_prefix = "STARLIGHT_"

settings = Settings()
