"""Pionex REST API client.

Auth:  HMAC-SHA256 signature
Signing (updated 2026-03-24 — Pionex changed POST/DELETE signing):
  - GET:    METHOD + PATH?sorted_query_params  (all params incl. timestamp in query)
  - POST:   METHOD + PATH?timestamp=TS + raw_body_json  (timestamp in query, body in JSON body)
  - DELETE: METHOD + PATH?timestamp=TS + raw_body_json  (timestamp in query, body in JSON body)
            signing string = f"{METHOD}{path}?timestamp={ts}{json.dumps(body)}"

Docs: https://pionex-doc.gitbook.io/apidocs
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Any

import httpx

_TIMEOUT = httpx.Timeout(15.0)
_BASE_URL = "https://api.pionex.com"


class PionexClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str = _BASE_URL) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._http = httpx.AsyncClient(base_url=base_url, timeout=_TIMEOUT)

    def _sign(self, method: str, path: str, params: dict) -> str:
        query = urllib.parse.urlencode(sorted(params.items()))
        payload = f"{method}{path}?{query}"
        return hmac.new(
            self._api_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    def _ts(self) -> int:
        return int(time.time() * 1000)

    async def _get(self, path: str, params: dict | None = None, signed: bool = False) -> Any:
        p = dict(params or {})
        if signed:
            p["timestamp"] = self._ts()
            sig = self._sign("GET", path, p)
            headers = {"PIONEX-KEY": self._api_key, "PIONEX-SIGNATURE": sig}
        else:
            headers = {}
        r = await self._http.get(path, params=p, headers=headers)
        r.raise_for_status()
        body = r.json()
        if not body.get("result"):
            raise RuntimeError(f"Pionex API error: {body.get('code')} {body.get('message')}")
        return body.get("data")

    async def _post(self, path: str, body: dict) -> Any:
        # Pionex POST signing: "POST/path?timestamp=TS" + raw_body_json (appended directly)
        # timestamp goes in query string; body params go in JSON body
        ts = self._ts()
        body = dict(body)
        body_json = json.dumps(body)
        sig_payload = f"POST{path}?timestamp={ts}{body_json}"
        sig = hmac.new(
            self._api_secret.encode(), sig_payload.encode(), hashlib.sha256
        ).hexdigest()
        headers = {
            "PIONEX-KEY": self._api_key,
            "PIONEX-SIGNATURE": sig,
            "Content-Type": "application/json",
        }
        r = await self._http.post(path, params={"timestamp": ts}, content=body_json.encode(), headers=headers)
        r.raise_for_status()
        res_body = r.json()
        if not res_body.get("result"):
            raise RuntimeError(f"Pionex API error: {res_body.get('code')} {res_body.get('message')}")
        return res_body.get("data")

    async def _delete(self, path: str, body: dict) -> Any:
        # Pionex DELETE signing: "DELETE/path?timestamp=TS" + raw_body_json (appended directly)
        # timestamp goes in query string; body params go in JSON body
        ts = self._ts()
        body_json = json.dumps(body)
        sig_payload = f"DELETE{path}?timestamp={ts}{body_json}"
        sig = hmac.new(
            self._api_secret.encode(), sig_payload.encode(), hashlib.sha256
        ).hexdigest()
        headers = {
            "PIONEX-KEY": self._api_key,
            "PIONEX-SIGNATURE": sig,
            "Content-Type": "application/json",
        }
        r = await self._http.request(
            "DELETE", path, params={"timestamp": ts}, content=body_json.encode(), headers=headers
        )
        r.raise_for_status()
        res_body = r.json()
        if not res_body.get("result"):
            raise RuntimeError(f"Pionex API error: {res_body.get('code')} {res_body.get('message')}")
        return res_body.get("data")

    # ── Market data (public) ──────────────────────────────────────────────

    async def get_symbols(self, type: str | None = None) -> list[dict[str, Any]]:
        """type: 'SPOT' or 'PERP'. Default SPOT if symbol not specified."""
        params: dict[str, Any] = {}
        if type:
            params["type"] = type.upper()
        data = await self._get("/api/v1/common/symbols", params=params)
        return data.get("symbols", [])

    async def get_ticker(
        self, symbol: str | None = None, type: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        if type and not symbol:
            params["type"] = type.upper()
        data = await self._get("/api/v1/market/tickers", params=params)
        return data.get("tickers", [])

    async def get_book_ticker(
        self, symbol: str | None = None, type: str | None = None
    ) -> list[dict[str, Any]]:
        """Best bid/ask price. type: 'SPOT' or 'PERP' (default PERP when symbol omitted)."""
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        elif type:
            params["type"] = type.upper()
        data = await self._get("/api/v1/market/bookTickers", params=params)
        return data.get("tickers", [])

    async def get_orderbook(self, symbol: str, depth: int = 20) -> dict[str, Any]:
        return await self._get(
            "/api/v1/market/depth",
            params={"symbol": symbol, "limit": depth},
        )

    async def get_klines(
        self,
        symbol: str,
        interval: str = "60M",
        limit: int = 100,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        """interval: 1M, 5M, 15M, 30M, 60M, 4H, 8H, 12H, 1D"""
        params: dict[str, Any] = {"symbol": symbol, "interval": interval, "limit": limit}
        if end_time:
            params["endTime"] = end_time
        data = await self._get("/api/v1/market/klines", params=params)
        return data.get("klines", []) if data else []

    async def get_recent_trades(
        self, symbol: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        data = await self._get(
            "/api/v1/market/trades",
            params={"symbol": symbol, "limit": limit},
        )
        return data.get("trades", []) if data else []

    # ── Account (private) ─────────────────────────────────────────────────

    async def get_balance(self) -> list[dict[str, Any]]:
        data = await self._get("/api/v1/account/balances", signed=True)
        return data.get("balances", [])

    async def get_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        data = await self._get(
            "/api/v1/trade/openOrders", params={"symbol": symbol}, signed=True
        )
        return data.get("orders", []) if data else []

    async def get_order_history(
        self,
        symbol: str,
        limit: int = 50,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"symbol": symbol, "limit": limit}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        data = await self._get("/api/v1/trade/allOrders", params=params, signed=True)
        return data.get("orders", []) if data else []

    async def get_order(self, order_id: str, symbol: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"orderId": order_id}
        if symbol:
            params["symbol"] = symbol
        data = await self._get("/api/v1/trade/order", params=params, signed=True)
        return data.get("order", {}) if data else {}

    async def get_order_by_client_order_id(
        self, client_order_id: str, symbol: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"clientOrderId": client_order_id}
        if symbol:
            params["symbol"] = symbol
        data = await self._get(
            "/api/v1/trade/orderByClientOrderId", params=params, signed=True
        )
        return data.get("order", {}) if data else {}

    async def get_my_trades(
        self, symbol: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        data = await self._get(
            "/api/v1/trade/myTrades",
            params={"symbol": symbol, "limit": limit},
            signed=True,
        )
        return data.get("trades", []) if data else []

    async def get_fills(
        self,
        symbol: str,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get fills (executed trades) for a symbol in a time range. Max 100 per query."""
        params: dict[str, Any] = {"symbol": symbol}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        data = await self._get("/api/v1/trade/fills", params=params, signed=True)
        return data.get("fills", []) if data else []

    async def get_fills_by_order_id(
        self, order_id: str, symbol: str | None = None, from_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Get all fills for a specific order."""
        params: dict[str, Any] = {"orderId": order_id}
        if symbol:
            params["symbol"] = symbol
        if from_id:
            params["fromId"] = from_id
        data = await self._get("/api/v1/trade/fillsByOrderId", params=params, signed=True)
        return data.get("fills", []) if data else []

    # ── Trading (write) ───────────────────────────────────────────────────

    async def create_order(
        self,
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
        Place a new order.
        - LIMIT: requires size + price
        - MARKET SELL: requires size
        - MARKET BUY: requires amount (USDT value to spend)
        - ioc: True for Immediate-Or-Cancel
        """
        body: dict[str, Any] = {
            "symbol": symbol,
            "side": side.upper(),
            "type": type.upper(),
        }
        if size is not None:
            body["size"] = size
        if price is not None:
            body["price"] = price
        if amount is not None:
            body["amount"] = amount
        if ioc:
            body["IOC"] = True
        if client_order_id:
            body["clientOrderId"] = client_order_id
        return await self._post("/api/v1/trade/order", body)

    async def create_mass_order(
        self, symbol: str, orders: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Place up to 20 LIMIT orders in a single request.
        Each order: {side, type, size, price, clientOrderId (optional)}
        """
        body = {"symbol": symbol, "orders": orders}
        data = await self._post("/api/v1/trade/massOrder", body)
        return data.get("orderIds", []) if data else []

    async def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        return await self._delete(
            "/api/v1/trade/order",
            body={"symbol": symbol, "orderId": int(order_id)},
        )

    async def batch_cancel_orders(
        self, symbol: str, order_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Cancel multiple specific orders sequentially (no batch API endpoint)."""
        results = []
        for oid in order_ids:
            try:
                await self.cancel_order(symbol, oid)
                results.append({"orderId": oid, "cancelled": True})
            except Exception as e:
                results.append({"orderId": oid, "cancelled": False, "error": str(e)})
        return results

    async def cancel_all_open_orders(self, symbol: str) -> dict[str, Any]:
        """Cancel ALL open orders for a symbol."""
        return await self._delete(
            "/api/v1/trade/allOrders",
            body={"symbol": symbol},
        )

    async def aclose(self) -> None:
        await self._http.aclose()
