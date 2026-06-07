from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_KEY: str = "placeholder_key"
    JWT_SECRET: str = "placeholder_secret"
    ALGORITHM: str = "HS256"

    class Config:
        env_file = ".env"

settings = Settings()