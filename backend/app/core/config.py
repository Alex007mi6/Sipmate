"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SipMate"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://sipmate:sipmate@localhost:5432/sipmate"

    secret_key: str = "change-me-in-production-use-long-random-string"
    access_token_expire_minutes: int = 60 * 24 * 7
    cookie_name: str = "sipmate_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    storage_backend: str = "local"  # local | cloudinary | s3
    local_upload_dir: str = "uploads"
    max_upload_bytes: int = 5 * 1024 * 1024

    admin_email: str = "admin@sipmate.example"
    admin_password: str = "change-me-admin-password"
    admin_display_name: str = "SipMate Admin"

    # Optional path to built SPA (frontend/dist). Empty disables static hosting.
    frontend_dist: str = "frontend/dist"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Normalize Neon/Supabase URLs for SQLAlchemy + psycopg."""
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
