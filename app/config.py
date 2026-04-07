from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load values from .env for local development.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = "development"
    app_port: int = 8000

    database_url: str

    telegram_bot_token: str
    telegram_webhook_secret: str
    public_base_url: str

    llm_api_key: str
    llm_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    optional_cleaning_model: str = "gpt-4o-mini"


settings = Settings()
