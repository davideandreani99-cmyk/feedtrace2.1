from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Connessione dell'applicazione: ruolo NON proprietario, soggetto a Row Level Security.
    database_url: str = "postgresql+psycopg://feedtrace_app:feedtrace_app@localhost:5432/feedtrace"
    # Connessione amministrativa: solo migrazioni, CLI di provisioning e test.
    admin_database_url: str = "postgresql+psycopg://feedtrace:feedtrace@localhost:5432/feedtrace"
    # Password con cui la migrazione crea il ruolo applicativo.
    app_db_password: str = "feedtrace_app"

    secret_key: str = "dev-only-cambiami"
    token_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:5173"]

    login_max_failures: int = 10
    login_window_seconds: int = 900


settings = Settings()
