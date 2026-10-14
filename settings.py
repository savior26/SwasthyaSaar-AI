from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "SwasthyaSaar"

    #Database
    DATABASE_URL: str 

    #Security
    SECRET_KEY: str
    EXPIRY: int = 30
    ALGORITHM: str
    
   


settings = Settings()


