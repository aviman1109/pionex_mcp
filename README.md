# pionex-mcp

Pionex trading MCP server. Exposes market data and order management via the [Pionex API](https://pionex-doc.gitbook.io/apidocs).

## Setup

1. Copy secrets template and fill in your API key:
   ```bash
   cp secrets/pionex.env.example secrets/pionex.env
   PIONEX_API_KEY=your_api_key_here
   PIONEX_API_SECRET=your_api_secret_here
   ```

2. Build and start:
   ```bash
   cd ~/ai-platform/mcps
   docker compose up -d --build pionex-mcp
   ```

3. Add to Claude Code:
   ```bash
   claude mcp add pionex --transport http http://127.0.0.1:38088/mcp
   ```

## MCP Tools

### Market Data (public, no auth required)
| Tool | Description |
|------|-------------|
| `list_symbols` | List all trading pairs; `type='SPOT'` (default) or `'PERP'` |
| `get_ticker` | 24h price stats; supports SPOT and PERP |
| `get_book_ticker` | Best bid/ask price and size (lighter than full orderbook) |
| `get_orderbook` | Full order book depth (max 1000 levels) |
| `get_klines` | OHLCV candles; intervals: 1M/5M/15M/30M/60M/4H/8H/12H/1D |
| `get_recent_trades` | Recent public trades |

### Account (read, requires API key)
| Tool | Description |
|------|-------------|
| `get_balance` | Trading account balances (free + frozen) |
| `get_open_orders` | Open orders for a symbol (max 200) |
| `get_order_history` | Historical orders with optional time range |
| `get_order` | Single order by exchange order ID |
| `get_order_by_client_order_id` | Single order by your own clientOrderId |
| `get_my_trades` | Personal trade fills for a symbol |
| `get_fills` | Fill records by time range (max 100 per query) |
| `get_fills_by_order_id` | All fills for a specific order |

### Trading (write) ⚠️
| Tool | Description |
|------|-------------|
| `create_order` | Place LIMIT or MARKET order (BUY supports `amount`; ioc supported) |
| `create_mass_order` | Place up to 20 LIMIT orders in a single call |
| `cancel_order` | Cancel a single order by ID |
| `batch_cancel_orders` | Cancel multiple specific orders by ID list |
| `cancel_all_open_orders` | Cancel ALL open orders for a symbol |

## Notes

- **PERP**: Perpetual futures **market data** is accessible via `type='PERP'` (list_symbols, get_ticker, get_book_ticker). **PERP order placement via API returns `TRADE_INVALID_SYMBOL`** — Pionex does not support Futures trading via the standard API key. Use the Pionex app/web for PERP positions.
- **Bot/Grid orders**: Pionex does not expose a public API for bot or grid trading. Grid bots must be managed via the Pionex web/mobile interface.
- **Balance**: Only includes the trading account; bot/earn account balances are excluded.
- **MARKET BUY**: Use `amount` (USDT to spend) instead of `size`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PIONEX_API_KEY` | *(required)* | Pionex API key |
| `PIONEX_API_SECRET` | *(required)* | Pionex API secret |
| `PIONEX_BASE_URL` | `https://api.pionex.com` | API base URL |
| `PORT` | `38088` | Server port |
| `MCP_TRANSPORT` | `http` | Transport mode |
| `MCP_HOST` | `0.0.0.0` | Bind address |
| `MCP_PATH` | `/mcp` | MCP endpoint path |
