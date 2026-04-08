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
    frontend_base_url: str | None = None
    auth_secret: str | None = None

    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None

    llm_api_key: str
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    embedding_model: str = "text-embedding-004"
    optional_cleaning_model: str = "gemini-2.0-flash-lite"


settings = Settings()
