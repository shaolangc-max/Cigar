from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    exchange_rate_api_key: str = ""
    scraper_concurrency: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
