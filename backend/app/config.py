from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    exchange_rate_api_key: str = ""
    scraper_concurrency: int = 5

    # JWT
    jwt_secret_key: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7天

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_monthly: str = ""   # Stripe 后台的月付 Price ID
    stripe_price_yearly: str = ""    # Stripe 后台的年付 Price ID
    frontend_url: str = "http://localhost:3001"

    # Admin 后台
    admin_username: str = "admin"
    admin_password: str = "cigar2026"

    class Config:
        env_file = ".env"


settings = Settings()
