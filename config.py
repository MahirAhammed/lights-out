from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    resend_api_key: str
    email_from: str
    secret_key: str
    frontend_url: str
    api_base_url: str
    
    class Config:
        env_file = ".env"

settings = Settings()