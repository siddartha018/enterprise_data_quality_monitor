from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


# Load .env from the project root so users don't have to export
_project_root = Path(__file__).resolve().parents[1]
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=False)


@dataclass(frozen=True)
class SnowflakeConfig:
    """Configuration required to connect to Snowflake.

    Secrets should be provided via environment variables or an external
    secret manager, never hardcoded in source code.
    """

    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str
    schema: str

    @classmethod
    def from_env(cls, prefix: str = "SNOWFLAKE_") -> "SnowflakeConfig":
        """Create a config instance from environment variables.

        Expected variables (assuming default prefix `SNOWFLAKE_`):
        - SNOWFLAKE_ACCOUNT
        - SNOWFLAKE_USER
        - SNOWFLAKE_PASSWORD
        - SNOWFLAKE_ROLE
        - SNOWFLAKE_WAREHOUSE
        - SNOWFLAKE_DATABASE
        - SNOWFLAKE_SCHEMA
        """

        def _get(name: str, required: bool = True) -> Optional[str]:
            value = os.getenv(f"{prefix}{name}")
            if required and not value:
                raise ValueError(f"Missing required environment variable: {prefix}{name}")
            return value

        return cls(
            account=_get("ACCOUNT") or "",
            user=_get("USER") or "",
            password=_get("PASSWORD") or "",
            role=_get("ROLE") or "",
            warehouse=_get("WAREHOUSE") or "",
            database=_get("DATABASE") or "",
            schema=_get("SCHEMA") or "",
        )

