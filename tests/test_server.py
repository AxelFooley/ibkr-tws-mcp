"""Tests for server module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ibkr_tws_mcp import server


class TestServerInitialization:
    """Tests for server initialization."""

    def test_init_tools(self) -> None:
        """Test tools initialization."""
        with patch("ibkr_tws_mcp.server.TWSClientWrapper") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            server.init_tools(
                host="127.0.0.1",
                port=7496,
                client_id=1,
                timeout=30,
            )

            mock_client_class.assert_called_once_with(
                host="127.0.0.1",
                port=7496,
                client_id=1,
                timeout=30,
            )

    def test_get_tools_lazy_initialization(self) -> None:
        """Test lazy initialization of tools when not explicitly initialized."""
        # Reset global tools
        server._tools = None

        with patch("ibkr_tws_mcp.server.TWSClientWrapper") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # get_tools should lazily initialize with defaults
            with patch.dict("os.environ", {}, clear=True):
                tools = server.get_tools()

            assert tools is not None
            mock_client_class.assert_called_once_with(
                host="127.0.0.1",
                port=7496,
                client_id=0,
                timeout=30,
            )

    def test_get_tools_handles_empty_env_vars(self) -> None:
        """Test that empty environment variables fall back to defaults."""
        # Reset global tools
        server._tools = None

        with patch("ibkr_tws_mcp.server.TWSClientWrapper") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # Empty strings should be treated like unset and use defaults
            env_with_empty = {
                "TWS_HOST": "",
                "TWS_PORT": "",
                "TWS_CLIENT_ID": "",
                "TWS_TIMEOUT": "",
            }
            with patch.dict("os.environ", env_with_empty, clear=True):
                tools = server.get_tools()

            assert tools is not None
            mock_client_class.assert_called_once_with(
                host="127.0.0.1",
                port=7496,
                client_id=0,
                timeout=30,
            )

    def test_get_tools_after_init(self) -> None:
        """Test getting tools after initialization."""
        with patch("ibkr_tws_mcp.server.TWSClientWrapper"):
            server.init_tools(
                host="127.0.0.1",
                port=7496,
                client_id=1,
                timeout=30,
            )

            tools = server.get_tools()
            assert tools is not None


class TestArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_parse_args_defaults(self) -> None:
        """Test argument parsing with defaults."""
        with patch("sys.argv", ["server"]):
            with patch.dict("os.environ", {}, clear=True):
                args = server.parse_args()

                assert args.tws_host == "127.0.0.1"
                assert args.tws_port == 7496
                assert args.tws_client_id == 0
                assert args.timeout == 30
                assert args.http_port == 8080
                assert args.http_host == "0.0.0.0"

    def test_parse_args_from_env(self) -> None:
        """Test argument parsing from environment variables."""
        env = {
            "TWS_HOST": "192.168.1.100",
            "TWS_PORT": "7497",
            "TWS_CLIENT_ID": "5",
            "TWS_TIMEOUT": "60",
            "MCP_HTTP_PORT": "9090",
            "MCP_HOST": "localhost",
        }

        with patch("sys.argv", ["server"]):
            with patch.dict("os.environ", env, clear=True):
                args = server.parse_args()

                assert args.tws_host == "192.168.1.100"
                assert args.tws_port == 7497
                assert args.tws_client_id == 5
                assert args.timeout == 60
                assert args.http_port == 9090
                assert args.http_host == "localhost"

    def test_parse_args_handles_empty_env_vars(self) -> None:
        """Test that empty environment variables fall back to defaults."""
        env_with_empty = {
            "TWS_HOST": "",
            "TWS_PORT": "",
            "TWS_CLIENT_ID": "",
            "TWS_TIMEOUT": "",
            "MCP_HTTP_PORT": "",
            "MCP_HOST": "",
        }

        with patch("sys.argv", ["server"]):
            with patch.dict("os.environ", env_with_empty, clear=True):
                args = server.parse_args()

                assert args.tws_host == "127.0.0.1"
                assert args.tws_port == 7496
                assert args.tws_client_id == 0
                assert args.timeout == 30
                assert args.http_port == 8080
                assert args.http_host == "0.0.0.0"

    def test_parse_args_from_cli(self) -> None:
        """Test argument parsing from command line."""
        with patch(
            "sys.argv",
            [
                "server",
                "--tws-host",
                "10.0.0.1",
                "--tws-port",
                "7498",
                "--tws-client-id",
                "10",
                "--timeout",
                "45",
                "--http-port",
                "8888",
                "--http-host",
                "0.0.0.0",
            ],
        ):
            args = server.parse_args()

            assert args.tws_host == "10.0.0.1"
            assert args.tws_port == 7498
            assert args.tws_client_id == 10
            assert args.timeout == 45
            assert args.http_port == 8888
            assert args.http_host == "0.0.0.0"
