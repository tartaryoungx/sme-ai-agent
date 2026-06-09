from pydantic_settings import BaseSettings
class Settings(BaseSettings):
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_KEY: str = "placeholder_key"
    JWT_SECRET: str = "placeholder_secret"
    ALGORITHM: str = "HS256"
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_BASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    GEMINI_API_KEY: str
   

    class Config:
        env_file = ".env"

settings = Settings()