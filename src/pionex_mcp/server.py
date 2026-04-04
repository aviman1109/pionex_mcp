"""Server bootstrap for the Pionex MCP server."""

from __future__ import annotations

import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
import uvicorn

from pionex_mcp.config import AppConfig, load_app_config
from pionex_mcp.pionex_client import PionexClient, _BASE_URL
from pionex_mcp.tools import register_tools


SERVER_INSTRUCTIONS = """
This MCP server exposes Pionex trading data and order management via the Pionex API.

Available capabilities:
- Market data: list_symbols, get_ticker, get_book_ticker, get_orderbook, get_klines, get_recent_trades
- Account: get_balance, get_open_orders, get_order_history, get_order, get_order_by_client_order_id, get_my_trades, get_fills, get_fills_by_order_id
- Trading (write): create_order, create_mass_order, cancel_order, batch_cancel_orders, cancel_all_open_orders

PERP support: list_symbols(type='PERP'), get_ticker(type='PERP'), get_book_ticker(type='PERP') for perpetual futures market data.

⚠️ Trading tools execute real orders. Always confirm details with the user before calling any write tool.
""".strip()


async def _oauth_disabled_endpoint(_request) -> JSONResponse:
    return JSONResponse({"error": "OAuth is disabled for this MCP server."}, status_code=404)


def _wrap_trailing_slash_compat(app, request_path: str):
    normalized_path = request_path if request_path.startswith("/") else f"/{request_path}"
    canonical_path = normalized_path.rstrip("/") or "/"
    alternate_path = canonical_path if normalized_path.endswith("/") else f"{canonical_path}/"

    async def wrapped(scope, receive, send):
        if scope["type"] == "http" and scope.get("path") == alternate_path:
            scope = dict(scope)
            scope["path"] = canonical_path
            root_path = scope.get("root_path", "")
            scope["raw_path"] = f"{root_path}{canonical_path}".encode()
        await app(scope, receive, send)

    return wrapped


def _wrap_octet_stream_compat(app, request_path: str):
    normalized_path = request_path if request_path.startswith("/") else f"/{request_path}"
    canonical_path = normalized_path.rstrip("/") or "/"

    async def wrapped(scope, receive, send):
        if scope["type"] == "http" and scope.get("method") == "POST":
            path = scope.get("path", "")
            if path in {canonical_path, f"{canonical_path}/"}:
                raw_headers = scope.get("headers", [])
                rewritten_headers = []
                changed = False
                saw_accept = False
                for key, value in raw_headers:
                    if key.lower() == b"content-type" and value.split(b";", 1)[0].strip() == b"application/octet-stream":
                        rewritten_headers.append((key, b"application/json"))
                        changed = True
                    elif key.lower() == b"accept":
                        saw_accept = True
                        lowered = value.lower()
                        has_json = b"application/json" in lowered
                        has_sse = b"text/event-stream" in lowered
                        has_wildcard = b"*/*" in lowered
                        if has_wildcard or not (has_json and has_sse):
                            rewritten_headers.append((key, b"application/json, text/event-stream"))
                            changed = True
                        else:
                            rewritten_headers.append((key, value))
                    else:
                        rewritten_headers.append((key, value))
                if not saw_accept:
                    rewritten_headers.append((b"accept", b"application/json, text/event-stream"))
                    changed = True
                if changed:
                    scope = dict(scope)
                    scope["headers"] = rewritten_headers
        await app(scope, receive, send)

    return wrapped


def _wrap_http_app(http_app, config: AppConfig) -> Starlette:
    wrapped_app = _wrap_trailing_slash_compat(http_app, config.path)
    wrapped_app = _wrap_octet_stream_compat(wrapped_app, config.path)

    lifespan = getattr(http_app.router, "lifespan_context", None)
    root_app = Starlette(
        lifespan=lifespan,
        routes=[
            Route(
                "/.well-known/oauth-protected-resource",
                _oauth_disabled_endpoint,
                methods=["GET"],
            ),
            Route(
                "/.well-known/oauth-protected-resource/{transport:path}",
                _oauth_disabled_endpoint,
                methods=["GET"],
            ),
            Route(
                "/.well-known/oauth-authorization-server",
                _oauth_disabled_endpoint,
                methods=["GET"],
            ),
            Route("/oauth/authorize", _oauth_disabled_endpoint, methods=["GET"]),
            Mount("", app=wrapped_app),
        ],
    )
    root_app.state.config = config
    return root_app


def build_app() -> tuple[FastMCP, AppConfig]:
    load_dotenv()
    config = load_app_config()
    client = PionexClient(
        api_key=config.api_key,
        api_secret=config.api_secret,
        base_url=config.base_url or _BASE_URL,
    )

    app = FastMCP(
        name="Pionex MCP",
        instructions=SERVER_INSTRUCTIONS,
    )
    app.settings.streamable_http_path = config.path
    app.settings.stateless_http = True
    app.settings.json_response = True
    app.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=config.allowed_hosts,
        allowed_origins=config.allowed_origins,
    )
    register_tools(app, client)
    return app, config


def main() -> None:
    try:
        app, config = build_app()
    except Exception as err:
        print(f"Server bootstrap failed: {err}", file=sys.stderr)
        raise

    print(f"Pionex MCP starting. Transport={config.transport}", file=sys.stderr)

    if config.transport in {"stdio", "STDIO"}:
        app.run()
        return

    transport = config.transport.lower()
    if transport in {"http", "streamable-http"}:
        http_app = _wrap_http_app(app.streamable_http_app(), config)
        uvicorn.run(http_app, host=config.host, port=config.port)
        return

    if transport == "sse":
        sse_app = app.sse_app(mount_path=config.path)
        uvicorn.run(sse_app, host=config.host, port=config.port)
        return

    raise ValueError(
        f"Unsupported transport '{config.transport}'. "
        "Use stdio, http, streamable-http, or sse."
    )


if __name__ == "__main__":
    main()
