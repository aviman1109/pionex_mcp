"""MCP tool definitions for the Pionex MCP server."""

from __future__ import annotations

import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

from pionex_mcp.pionex_client import PionexClient


def register_tools(app: FastMCP, client: PionexClient) -> None:

    # ── Market data ───────────────────────────────────────────────────────

    @app.tool()
    async def list_symbols() -> list[dict[str, Any]]:
        """List all available trading pairs on Pionex (symbol, type, base/quote currency)."""
        return await client.get_symbols()

    @app.tool()
    async def get_ticker(symbol: str | None = None) -> list[dict[str, Any]]:
        """
        Get market ticker (price, 24h volume, high/low, change).
        Leave symbol empty to get all tickers.
        Example symbol: 'BTC_USDT'
        """
        return await client.get_ticker(symbol=symbol)

    @app.tool()
    async def get_orderbook(symbol: str, depth: int = 20) -> dict[str, Any]:
        """
        Get order book (bids and asks) for a symbol.
        depth: number of price levels (default 20).
        Example symbol: 'BTC_USDT'
        """
        return await client.get_orderbook(symbol=symbol, depth=depth)

    @app.tool()
    async def get_klines(
        symbol: str,
        interval: str = "1H",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get OHLCV candlestick data.
        interval: '1M', '5M', '15M', '30M', '1H', '4H', '1D', '1W'
        limit: number of candles (default 100).
        Example symbol: 'BTC_USDT'
        """
        return await client.get_klines(symbol=symbol, interval=interval, limit=limit)

    @app.tool()
    async def get_recent_trades(symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get recent public trades for a symbol.
        Example symbol: 'BTC_USDT'
        """
        return await client.get_recent_trades(symbol=symbol, limit=limit)

    # ── Account ───────────────────────────────────────────────────────────

    @app.tool()
    async def get_balance() -> list[dict[str, Any]]:
        """Get account balances — free (available) and frozen amounts for each asset."""
        return await client.get_balance()

    @app.tool()
    async def get_open_orders(symbol: str | None = None) -> list[dict[str, Any]]:
        """
        List currently open orders.
        Optionally filter by symbol, e.g. 'BTC_USDT'.
        """
        return await client.get_open_orders(symbol=symbol)

    @app.tool()
    async def get_order_history(
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get historical orders (filled, cancelled, etc.).
        Optionally filter by symbol.
        """
        return await client.get_order_history(symbol=symbol, limit=limit)

    @app.tool()
    async def get_order(order_id: str) -> dict[str, Any]:
        """Get details of a specific order by order_id."""
        return await client.get_order(order_id=order_id)

    @app.tool()
    async def get_my_trades(symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get personal trade history (executed fills) for a symbol.
        Example symbol: 'BTC_USDT'
        """
        return await client.get_my_trades(symbol=symbol, limit=limit)

    # ── Trading (write) ───────────────────────────────────────────────────

    @app.tool()
    async def create_order(
        symbol: str,
        side: str,
        type: str,
        size: str,
        price: str | None = None,
        time_in_force: str = "GTC",
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Place a new order. ⚠️ This executes a real trade — confirm before calling.

        symbol: e.g. 'BTC_USDT'
        side: 'BUY' or 'SELL'
        type: 'LIMIT' or 'MARKET'
        size: quantity of base asset (as string, e.g. '0.001')
        price: required for LIMIT orders (as string, e.g. '80000')
        time_in_force: 'GTC' (default), 'IOC', 'FOK'
        client_order_id: optional unique ID you assign
        """
        if type.upper() == "LIMIT" and price is None:
            raise ValueError("price is required for LIMIT orders.")
        coid = client_order_id or f"mcp-{uuid.uuid4().hex[:16]}"
        return await client.create_order(
            symbol=symbol,
            side=side,
            type=type,
            size=size,
            price=price,
            time_in_force=time_in_force,
            client_order_id=coid,
        )

    @app.tool()
    async def cancel_order(symbol: str, order_id: str) -> dict[str, Any]:
        """
        Cancel an open order. ⚠️ This cancels a real order — confirm before calling.
        symbol: e.g. 'BTC_USDT'
        order_id: the order ID to cancel
        """
        return await client.cancel_order(symbol=symbol, order_id=order_id)
