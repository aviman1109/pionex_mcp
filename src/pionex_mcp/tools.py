"""MCP tool definitions for the Pionex MCP server."""

from __future__ import annotations

import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

from pionex_mcp.pionex_client import PionexClient


def register_tools(app: FastMCP, client: PionexClient) -> None:

    # ── Market data (public) ──────────────────────────────────────────────

    @app.tool()
    async def list_symbols(type: str = "SPOT") -> list[dict[str, Any]]:
        """
        List all available trading pairs.
        type: 'SPOT' (default) or 'PERP' for perpetual futures.
        Returns symbol, baseCurrency, quoteCurrency, min/max trade sizes, etc.
        """
        return await client.get_symbols(type=type)

    @app.tool()
    async def get_ticker(
        symbol: str | None = None,
        type: str = "SPOT",
    ) -> list[dict[str, Any]]:
        """
        Get 24h market ticker (price, volume, high/low, change).
        symbol: e.g. 'BTC_USDT' or 'BTC_USDT_PERP'. Leave empty for all tickers.
        type: 'SPOT' (default) or 'PERP' — only used when symbol is not specified.
        """
        return await client.get_ticker(symbol=symbol, type=type)

    @app.tool()
    async def get_book_ticker(
        symbol: str | None = None,
        type: str = "SPOT",
    ) -> list[dict[str, Any]]:
        """
        Get best bid/ask price and size (top of order book).
        symbol: e.g. 'BTC_USDT'. Leave empty for all symbols of the given type.
        type: 'SPOT' or 'PERP' — only used when symbol is not specified (default PERP).
        Faster and lighter than get_orderbook when you only need the best price.
        """
        return await client.get_book_ticker(symbol=symbol, type=type)

    @app.tool()
    async def get_orderbook(symbol: str, depth: int = 20) -> dict[str, Any]:
        """
        Get order book (bids and asks) for a symbol.
        depth: number of price levels (default 20, max 1000).
        Example symbol: 'BTC_USDT'
        """
        return await client.get_orderbook(symbol=symbol, depth=depth)

    @app.tool()
    async def get_klines(
        symbol: str,
        interval: str = "60M",
        limit: int = 100,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get OHLCV candlestick data.
        interval: '1M', '5M', '15M', '30M', '60M', '4H', '8H', '12H', '1D'
        limit: number of candles (default 100, max 500).
        end_time: optional end timestamp in milliseconds.
        Example symbol: 'BTC_USDT'
        """
        return await client.get_klines(
            symbol=symbol, interval=interval, limit=limit, end_time=end_time
        )

    @app.tool()
    async def get_recent_trades(symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get recent public trades for a symbol (taker's perspective).
        limit: 10–500, default 50.
        Example symbol: 'BTC_USDT'
        """
        return await client.get_recent_trades(symbol=symbol, limit=limit)

    # ── Account (read) ────────────────────────────────────────────────────

    @app.tool()
    async def get_balance() -> list[dict[str, Any]]:
        """
        Get trading account balances — free (available) and frozen per asset.
        Note: excludes bot and earn account balances.
        """
        return await client.get_balance()

    @app.tool()
    async def get_open_orders(symbol: str) -> list[dict[str, Any]]:
        """
        List currently open orders for a symbol.
        symbol: e.g. 'BTC_USDT' (required — max 200 open orders per symbol).
        """
        return await client.get_open_orders(symbol=symbol)

    @app.tool()
    async def get_order_history(
        symbol: str,
        limit: int = 50,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get historical orders (filled, cancelled, etc.) for a symbol.
        symbol: e.g. 'BTC_USDT' (required).
        limit: 1–200, default 50.
        start_time / end_time: optional timestamps in milliseconds.
        """
        return await client.get_order_history(
            symbol=symbol, limit=limit, start_time=start_time, end_time=end_time
        )

    @app.tool()
    async def get_order(order_id: str, symbol: str | None = None) -> dict[str, Any]:
        """
        Get details of a specific order by order_id.
        symbol: recommended for faster lookup (e.g. 'BTC_USDT').
        """
        return await client.get_order(order_id=order_id, symbol=symbol)

    @app.tool()
    async def get_order_by_client_order_id(
        client_order_id: str, symbol: str | None = None
    ) -> dict[str, Any]:
        """
        Get order details using your own clientOrderId instead of the exchange order_id.
        symbol: recommended for faster lookup.
        """
        return await client.get_order_by_client_order_id(
            client_order_id=client_order_id, symbol=symbol
        )

    @app.tool()
    async def get_my_trades(symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get personal trade history (executed fills) for a symbol.
        Example symbol: 'BTC_USDT'
        """
        return await client.get_my_trades(symbol=symbol, limit=limit)

    @app.tool()
    async def get_fills(
        symbol: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get fill records (individual executions) for a symbol in a time range.
        Returns TAKER/MAKER role, price, size, fee per fill. Max 100 per query.
        start_time / end_time: timestamps in milliseconds.
        Example symbol: 'BTC_USDT'
        """
        return await client.get_fills(
            symbol=symbol, start_time=start_time, end_time=end_time
        )

    @app.tool()
    async def get_fills_by_order_id(
        order_id: str,
        symbol: str | None = None,
        from_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get all fill records for a specific order_id.
        from_id: return fills before this fill_id (pagination).
        """
        return await client.get_fills_by_order_id(
            order_id=order_id, symbol=symbol, from_id=from_id
        )

    # ── Trading (write) ───────────────────────────────────────────────────

    @app.tool()
    async def create_order(
        symbol: str,
        side: str,
        type: str,
        size: str | None = None,
        price: str | None = None,
        amount: str | None = None,
        ioc: bool = False,
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Place a new order. ⚠️ Executes a real trade — confirm before calling.

        symbol: e.g. 'BTC_USDT'
        side: 'BUY' or 'SELL'
        type: 'LIMIT' or 'MARKET'

        For LIMIT orders:    size + price required
        For MARKET SELL:     size required (quantity of base asset)
        For MARKET BUY:      amount required (USDT value to spend, e.g. '100')

        ioc: True = Immediate-Or-Cancel (fill immediately or cancel remainder)
        client_order_id: optional unique ID you assign (letters/numbers/hyphen, max 64 chars)
        """
        t = type.upper()
        s = side.upper()
        if t == "LIMIT":
            if size is None or price is None:
                raise ValueError("LIMIT orders require both size and price.")
        elif t == "MARKET":
            if s == "SELL" and size is None:
                raise ValueError("MARKET SELL requires size.")
            if s == "BUY" and amount is None:
                raise ValueError("MARKET BUY requires amount (USDT value to spend).")

        coid = client_order_id or f"mcp-{uuid.uuid4().hex[:16]}"
        return await client.create_order(
            symbol=symbol,
            side=side,
            type=type,
            size=size,
            price=price,
            amount=amount,
            ioc=ioc,
            client_order_id=coid,
        )

    @app.tool()
    async def create_mass_order(
        symbol: str,
        orders: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Place up to 20 LIMIT orders in a single API call. ⚠️ Confirm before calling.

        symbol: e.g. 'BTC_USDT'
        orders: list of order dicts, each with:
          - side: 'BUY' or 'SELL'
          - type: 'LIMIT' (only LIMIT supported)
          - size: quantity (string)
          - price: price (string)
          - clientOrderId: optional unique ID (string)

        Example:
          orders = [
            {"side": "BUY", "type": "LIMIT", "size": "0.001", "price": "80000"},
            {"side": "BUY", "type": "LIMIT", "size": "0.001", "price": "79000"},
          ]

        Returns list of {orderId, clientOrderId}.
        """
        if not orders:
            raise ValueError("orders list must not be empty.")
        if len(orders) > 20:
            raise ValueError("Maximum 20 orders per batch.")
        for i, o in enumerate(orders):
            if o.get("type", "").upper() != "LIMIT":
                raise ValueError(f"orders[{i}]: only LIMIT type is supported in mass orders.")
            if not o.get("size") or not o.get("price"):
                raise ValueError(f"orders[{i}]: size and price are required.")
            if "clientOrderId" not in o:
                o["clientOrderId"] = f"mcp-{uuid.uuid4().hex[:16]}"
        return await client.create_mass_order(symbol=symbol, orders=orders)

    @app.tool()
    async def cancel_order(symbol: str, order_id: str) -> dict[str, Any]:
        """
        Cancel a single open order. ⚠️ Confirm before calling.
        symbol: e.g. 'BTC_USDT'
        order_id: the exchange order ID to cancel
        """
        return await client.cancel_order(symbol=symbol, order_id=order_id)

    @app.tool()
    async def batch_cancel_orders(
        symbol: str,
        order_ids: list[str],
    ) -> list[dict[str, Any]]:
        """
        Cancel specific orders by ID list. ⚠️ Confirm before calling.
        Cancels each order sequentially and reports per-order success/failure.
        symbol: e.g. 'BTC_USDT'
        order_ids: list of exchange order IDs to cancel
        """
        if not order_ids:
            raise ValueError("order_ids must not be empty.")
        return await client.batch_cancel_orders(symbol=symbol, order_ids=order_ids)

    @app.tool()
    async def cancel_all_open_orders(symbol: str) -> dict[str, Any]:
        """
        Cancel ALL open orders for a symbol in one call. ⚠️ Irreversible — confirm before calling.
        symbol: e.g. 'BTC_USDT'
        """
        return await client.cancel_all_open_orders(symbol=symbol)
