from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # ATS ingestion. These are operational controls rather than provider
    # parsing policy, so deployments can tune them without changing code.
    ats_http_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    ats_max_response_mb: int = Field(default=50, ge=1, le=100)
    ats_max_attempts: int = Field(default=3, ge=1, le=5)
    ats_global_concurrency: int = Field(default=12, ge=1, le=100)
    ats_http_max_connections: int = Field(default=20, ge=1, le=200)
    ats_http_max_keepalive_connections: int = Field(default=10, ge=0, le=200)

    @property
    def ats_max_response_bytes(self) -> int:
        return self.ats_max_response_mb * 1024 * 1024

    @model_validator(mode="after")
    def validate_ats_connection_pool(self) -> Self:
        if self.ats_http_max_keepalive_connections > self.ats_http_max_connections:
            raise ValueError(
                "ats_http_max_keepalive_connections cannot exceed ats_http_max_connections"
            )
        return self

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"
    cookie_secure: bool = False

    # CORS — comma-separated list of allowed frontend origins.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # Google OAuth ("Continue with Google"). The client id is the OAuth 2.0
    # Web client id from Google Cloud Console; empty disables the feature.
    google_client_id: str = ""

    # AI — set at least one key; providers are tried in order: Groq → Gemini → OpenAI
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    # Uploads
    max_upload_mb: int = 5
    max_resumes_per_user: int = 2

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    # AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"


settings = Settings()
