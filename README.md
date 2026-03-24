# pionex-mcp

Pionex trading MCP server. Exposes market data and order management via the [Pionex API](https://github.com/pionex-doc/sdk-python) (bitmake SDK).

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
| `list_symbols` | List all available trading pairs |
| `get_ticker` | Price and 24h stats (all or specific symbol) |
| `get_orderbook` | Order book depth |
| `get_klines` | OHLCV candlestick data |
| `get_recent_trades` | Recent public trades |

### Account (read)
| Tool | Description |
|------|-------------|
| `get_balance` | Asset balances (available + total) |
| `get_open_orders` | Currently open orders |
| `get_order_history` | Historical orders |
| `get_order` | Single order by ID |
| `get_my_trades` | Personal trade fills |

### Trading (write) ⚠️
| Tool | Description |
|------|-------------|
| `create_order` | Place a limit or market order |
| `cancel_order` | Cancel a single order |

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
