from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # Google OAuth ("Continue with Google"). The client id is the OAuth 2.0
    # Web client id from Google Cloud Console; empty disables the feature.
    google_client_id: str = ""

    # Uploads
    max_upload_mb: int = 5

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    # AI
    gemini_api_key: str = ""
    openai_api_key: str = ""


settings = Settings()