from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql://localhost/tabular"

    # Supabase Auth
    supabase_url: str = ""
    supabase_jwt_secret: str = ""

    # CORS (comma-separated origins, e.g. http://localhost:3000,https://app.tabular.com)
    cors_origins: str = "http://localhost:3000"

    # PDF limits
    max_pdf_bytes: int = 25 * 1024 * 1024  # 25 MB
    max_pdf_pages: int = 50

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
