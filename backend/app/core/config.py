# backend/app/core/config.py
## This file contains the application settings and configuration.
# It loads environment variables from a .env file and provides default values for various settings.
import os
from dotenv import load_dotenv
from os import getenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    RESET_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", 15))
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    ENV: str = os.getenv("ENV", "development")
    INVOICE_MARGIN_ALERT_THRESHOLD = 25.0  # percent
    SUBSTITUTION_REORDER_THRESHOLD = 3
    UNIT_COST_ALERT_THRESHOLD = 1.15  # 15% above last known cost
    MAX_BAY_JOBS_PER_DAY = 12




settings = Settings()
