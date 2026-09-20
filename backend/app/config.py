from pydantic_settings import BaseSettings
from typing import List
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    API_TITLE: str = "StarGuard API"
    DEBUG: bool = True
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Read from the environment or backend/.env. real_data.py reads
    # os.environ directly, so the real-scan route bridges this across.
    GITHUB_TOKEN: str = ""

    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    DATABASE_PATH: str = os.path.join(BASE_DIR, "data", "starguard.db")
    MODEL_PATH: str = os.path.join(BASE_DIR, "data", "gnn_model.pt")

    # Synthetic data generation
    NUM_NORMAL_USERS: int = 1400
    NUM_FRAUD_USERS: int = 312
    NUM_REPOS: int = 1204
    NUM_FRAUD_CLUSTERS: int = 9
    RANDOM_SEED: int = 42

    RISK_THRESHOLDS: dict = {
        "critical": 80,
        "high": 60,
        "watch": 40,
    }

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
os.makedirs(settings.DATA_DIR, exist_ok=True)
