from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str   
    supabase_url: str
    supabase_key: str  # anon key (used for public reads)
    supabase_service_key: str  # service role key (used for server-side storage writes)
    supabase_bucket: str
    admin_key: str
    allowed_origins: list[str] = ["http://localhost:3000"]
    frontend_url: str = "http://localhost:3000"


settings = Settings()

MAX_FILES = 5
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_TOTAL_FILE_SIZE = 40 * 1024 * 1024  # 40 MB total (headroom for 52 MB body limit)
