import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    # PostgreSQL
    PG_HOST: str = os.getenv("PG_HOST", "localhost")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
    PG_DB: str = os.getenv("PG_DB", "advertisements_db")
    PG_USER: str = os.getenv("PG_USER", "postgres")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD", "postgres")

    # HTTP
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "5000"))

    @property
    def dsn(self) -> str:
        # asyncpg DSN
        return (
            f"postgresql://{self.PG_USER}:{self.PG_PASSWORD}"
            f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"
        )