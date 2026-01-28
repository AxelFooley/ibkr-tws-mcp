# Multi-stage build for IBKR TWS MCP Server
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./
COPY src ./src

# Install dependencies using uv
RUN uv pip install --system --no-cache -e .

# Production stage
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src ./src
COPY pyproject.toml README.md ./

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Default environment variables
ENV TWS_HOST=127.0.0.1 \
    TWS_PORT=7496 \
    TWS_CLIENT_ID=0 \
    TWS_TIMEOUT=30 \
    MCP_HOST=0.0.0.0 \
    MCP_HTTP_PORT=8080

# Expose HTTP port
EXPOSE 8080

# Run the MCP server
ENTRYPOINT ["python", "-m", "ibkr_tws_mcp.server"]
CMD []
