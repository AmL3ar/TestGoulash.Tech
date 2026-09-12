from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Навигатор поставщиков — без LLM"
    database_url: str = "sqlite:///./supplier_scout.db"
    live_search_limit: int = 5
    serper_api_key: str | None = None
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
