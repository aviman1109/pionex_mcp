"""Pionex REST API client.

Auth:  HMAC-SHA256 signature
Payload format: METHOD + path + ? + query_string
Headers: PIONEX-KEY, PIONEX-SIGNATURE
Timestamp in query string as `timestamp` param.

Docs: https://pionex-doc.gitbook.io/apidocs
"""

from __future__ import annotations

import hashlib
import hmac
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

    def _ts(self) -> str:
        return str(int(time.time() * 1000))

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
        ts = self._ts()
        body["timestamp"] = ts
        query = urllib.parse.urlencode(sorted(body.items()))
        payload = f"POST{path}?{query}"
        sig = hmac.new(
            self._api_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        headers = {
            "PIONEX-KEY": self._api_key,
            "PIONEX-SIGNATURE": sig,
            "Content-Type": "application/json",
        }
        r = await self._http.post(path, json=body, headers=headers)
        r.raise_for_status()
        res_body = r.json()
        if not res_body.get("result"):
            raise RuntimeError(f"Pionex API error: {res_body.get('code')} {res_body.get('message')}")
        return res_body.get("data")

    async def _delete(self, path: str, params: dict) -> Any:
        params["timestamp"] = self._ts()
        sig = self._sign("DELETE", path, params)
        headers = {"PIONEX-KEY": self._api_key, "PIONEX-SIGNATURE": sig}
        r = await self._http.delete(path, params=params, headers=headers)
        r.raise_for_status()
        body = r.json()
        if not body.get("result"):
            raise RuntimeError(f"Pionex API error: {body.get('code')} {body.get('message')}")
        return body.get("data")

    # ── Market data (public) ──────────────────────────────────────────────

    async def get_symbols(self) -> list[dict[str, Any]]:
        data = await self._get("/api/v1/common/symbols")
        return data.get("symbols", [])

    async def get_ticker(self, symbol: str | None = None) -> list[dict[str, Any]]:
        params = {}
        if symbol:
            params["symbol"] = symbol
        data = await self._get("/api/v1/market/tickers", params=params)
        return data.get("tickers", [])

    async def get_orderbook(self, symbol: str, depth: int = 20) -> dict[str, Any]:
        return await self._get(
            "/api/v1/market/depth",
            params={"symbol": symbol, "depth": depth},
        )

    async def get_klines(
        self, symbol: str, interval: str = "1H", limit: int = 100
    ) -> list[dict[str, Any]]:
        data = await self._get(
            "/api/v1/market/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
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

    async def get_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]:
        params = {}
        if symbol:
            params["symbol"] = symbol
        data = await self._get("/api/v1/trade/openOrders", params=params, signed=True)
        return data.get("orders", []) if data else []

    async def get_order_history(
        self, symbol: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
        data = await self._get("/api/v1/trade/orderHistory", params=params, signed=True)
        return data.get("orders", []) if data else []

    async def get_order(self, order_id: str) -> dict[str, Any]:
        data = await self._get(
            "/api/v1/trade/order", params={"orderId": order_id}, signed=True
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

    # ── Trading (write) ───────────────────────────────────────────────────

    async def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        size: str,
        price: str | None = None,
        time_in_force: str = "GTC",
        client_order_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "symbol": symbol,
            "side": side.upper(),
            "type": type.upper(),
            "size": size,
            "timeInForce": time_in_force.upper(),
        }
        if price is not None:
            body["price"] = price
        if client_order_id:
            body["clientOrderId"] = client_order_id
        return await self._post("/api/v1/trade/order", body)

    async def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        return await self._delete(
            "/api/v1/trade/order",
            params={"symbol": symbol, "orderId": order_id},
        )

    async def aclose(self) -> None:
        await self._http.aclose()
