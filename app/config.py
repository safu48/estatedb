import os
from urllib.parse import quote_plus, unquote, urlparse
from dotenv import load_dotenv

# Load variables from a local .env file if present.
load_dotenv()


class Settings:
    """Central place for every configurable value in the app."""

    _raw_db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRESQL_URL")
    )
    if _raw_db_url:
        # Standardize postgres:// to postgresql:// for compatibility
        if _raw_db_url.startswith("postgres://"):
            _db_url = "postgresql://" + _raw_db_url[len("postgres://"):]
        else:
            _db_url = _raw_db_url

        _parsed = urlparse(_db_url)
        DB_USER: str = unquote(_parsed.username or "postgres")
        DB_PASSWORD: str = unquote(_parsed.password or "")
        DB_HOST: str = _parsed.hostname or "localhost"
        DB_PORT: int = _parsed.port or 5432
        DB_NAME: str = _parsed.path.lstrip("/") or "estatedb"
    else:
        _db_url = None
        # --- PostgreSQL connection (defaults for local PostgreSQL) ---
        DB_USER: str = os.getenv("DB_USER", "postgres")
        DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
        DB_HOST: str = os.getenv("DB_HOST", "localhost")
        DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
        DB_NAME: str = os.getenv("DB_NAME", "estatedb")

    # SSL connection support for remote cloud databases (Render, Neon, Supabase, etc.)
    DB_SSL: bool = os.getenv("DB_SSL", "false").lower() in ("true", "1", "yes")

    DATABASE_URL: str = _db_url or ""

    # --- Web app ---
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("PORT", os.getenv("APP_PORT", "8000")))

    def get_conninfo(self) -> str:
        """Return the PostgreSQL connection string with SSL parameters if configured."""
        if self._db_url:
            url = self._db_url
            is_cloud = any(cloud in url for cloud in ("neon.tech", "supabase.co", "render.com", "aivencloud.com"))
            if (is_cloud or self.DB_SSL) and "sslmode" not in url:
                delim = "&" if "?" in url else "?"
                url = f"{url}{delim}sslmode=require"
            return url

        pwd_part = f":{quote_plus(self.DB_PASSWORD)}" if self.DB_PASSWORD else ""
        conn_str = f"postgresql://{quote_plus(self.DB_USER)}{pwd_part}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        if self.DB_SSL:
            conn_str += "?sslmode=require"
        return conn_str


settings = Settings()
