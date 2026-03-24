"""Configuration helpers for the Pionex MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _parse_csv_env(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class AppConfig:
    api_key: str
    api_secret: str
    base_url: str
    transport: str
    host: str
    port: int
    path: str
    allowed_hosts: list[str]
    allowed_origins: list[str]


def load_app_config() -> AppConfig:
    api_key = os.getenv("PIONEX_API_KEY", "")
    api_secret = os.getenv("PIONEX_API_SECRET", "")
    if not api_key or not api_secret:
        raise ValueError(
            "PIONEX_API_KEY and PIONEX_API_SECRET must be set. "
            "Add them to secrets/pionex.env."
        )

    default_allowed_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    default_allowed_origins = [
        "http://127.0.0.1:*",
        "http://localhost:*",
        "http://[::1]:*",
    ]

    return AppConfig(
        api_key=api_key,
        api_secret=api_secret,
        base_url=os.getenv("PIONEX_BASE_URL", "https://api.pionex.com"),
        transport=os.getenv("MCP_TRANSPORT", "http"),
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "38088")),
        path=os.getenv("MCP_PATH", "/mcp"),
        allowed_hosts=default_allowed_hosts + _parse_csv_env(os.getenv("MCP_ALLOWED_HOSTS")),
        allowed_origins=default_allowed_origins
        + _parse_csv_env(os.getenv("MCP_ALLOWED_ORIGINS")),
    )
