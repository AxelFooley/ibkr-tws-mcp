# IBKR TWS MCP Server

An MCP (Model Context Protocol) server that provides LLMs with access to Interactive Brokers Trader Workstation (TWS) functionality via the ibapi library.

## Features

- **Connection Management**: Connect/disconnect from TWS, check connection status
- **Account Data**: Get account summary, managed accounts, positions
- **Order Management**: Place, cancel, and monitor orders
- **Market Data**: Real-time quotes and historical OHLCV data
- **Contract Lookup**: Search and get details for any tradeable instrument
- **Execution Reports**: View filled orders and commissions
- **P&L Tracking**: Account and position-level profit/loss
- **Market Scanners**: Access TWS market scanner functionality
- **News**: Historical news headlines and article content

## Prerequisites

- Python 3.11+
- Interactive Brokers TWS or IB Gateway running with API enabled
- TWS API settings configured to allow connections

### TWS Configuration

1. Open TWS or IB Gateway
2. Go to **Edit** → **Global Configuration** → **API** → **Settings**
3. Enable **Enable ActiveX and Socket Clients**
4. Set **Socket port** (default: 7496 for live, 7497 for paper)
5. Add your IP to **Trusted IPs** (or enable from localhost only)
6. Uncheck **Read-Only API** if you want to place orders

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/AxelFooley/ibkr-tws-mcp.git
cd ibkr-tws-mcp

# Install dependencies
uv sync --all-extras

# Run the server
uv run python -m ibkr_tws_mcp.server
```

### Using pip

```bash
pip install ibkr-tws-mcp
ibkr-tws-mcp
```

### Using Docker

```bash
# Build and run
docker compose up --build

# Or pull from registry
docker pull ghcr.io/axelfooley/ibkr-tws-mcp:latest
docker run -p 8080:8080 \
  -e TWS_HOST=host.docker.internal \
  -e TWS_PORT=7496 \
  ghcr.io/axelfooley/ibkr-tws-mcp:latest
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TWS_HOST` | TWS/IB Gateway host address | `127.0.0.1` |
| `TWS_PORT` | TWS API port (7496=live, 7497=paper) | `7496` |
| `TWS_CLIENT_ID` | Unique client ID (0-32) | `0` |
| `TWS_TIMEOUT` | Request timeout in seconds | `30` |
| `MCP_HOST` | MCP server bind address | `0.0.0.0` |
| `MCP_HTTP_PORT` | MCP server port | `8080` |

### Command Line Arguments

```bash
python -m ibkr_tws_mcp.server \
  --tws-host 127.0.0.1 \
  --tws-port 7496 \
  --tws-client-id 0 \
  --timeout 30 \
  --http-host 0.0.0.0 \
  --http-port 8080
```

## Available Tools

### Connection

- `tws_connect` - Connect to TWS
- `tws_disconnect` - Disconnect from TWS
- `tws_connection_status` - Check connection status
- `tws_get_server_time` - Get TWS server time

### Account

- `tws_get_managed_accounts` - List managed accounts
- `tws_get_account_summary` - Get account balances, margin, etc.

### Positions

- `tws_get_positions` - Get all current positions

### Orders

- `tws_place_order` - Place a new order
- `tws_cancel_order` - Cancel an order
- `tws_cancel_all_orders` - Cancel all open orders
- `tws_get_open_orders` - Get open orders for this client
- `tws_get_all_open_orders` - Get all open orders

### Market Data

- `tws_get_market_data` - Get real-time market data snapshot
- `tws_get_historical_data` - Get historical OHLCV bars

### Contracts

- `tws_get_contract_details` - Get contract specifications
- `tws_search_contracts` - Search for contracts by symbol

### Executions

- `tws_get_executions` - Get execution reports

### P&L

- `tws_get_pnl` - Get account P&L
- `tws_get_position_pnl` - Get position-level P&L

### Scanners

- `tws_get_scanner_parameters` - Get available scanner parameters

### News

- `tws_get_news_providers` - List news providers
- `tws_get_historical_news` - Get historical news headlines
- `tws_get_news_article` - Get news article content

## Usage Example

Once connected to the MCP server, an LLM can interact with TWS:

```
User: Connect to TWS and show me my account summary