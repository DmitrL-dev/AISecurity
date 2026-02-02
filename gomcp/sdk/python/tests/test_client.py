"""
Tests for GoMCP Python SDK.
"""

import json
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError
from io import BytesIO

from gomcp import (
    GoMCPClient,
    GoMCPError,
    ConnectionError,
    ValidationError,
    ToolNotFoundError,
    ToolInfo,
    ToolResult,
    BatchRequest,
    BatchResult,
    HealthStatus,
    create_client,
    __version__,
)


class TestVersion(unittest.TestCase):
    def test_version_exists(self):
        self.assertIsNotNone(__version__)
        self.assertEqual(__version__, "1.0.0")


class TestToolInfo(unittest.TestCase):
    def test_create(self):
        info = ToolInfo(name="test", description="Test tool")
        self.assertEqual(info.name, "test")
        self.assertEqual(info.description, "Test tool")

    def test_with_schema(self):
        schema = {"type": "object"}
        info = ToolInfo(name="test", input_schema=schema)
        self.assertEqual(info.input_schema, schema)


class TestToolResult(unittest.TestCase):
    def test_success(self):
        result = ToolResult(output={"data": 1}, success=True)
        self.assertTrue(result.success)
        self.assertIsNone(result.error)

    def test_failure(self):
        result = ToolResult(output=None, success=False, error="failed")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "failed")


class TestBatchRequest(unittest.TestCase):
    def test_create(self):
        req = BatchRequest(id="1", tool="echo", arguments={"msg": "hi"})
        self.assertEqual(req.id, "1")
        self.assertEqual(req.tool, "echo")
        self.assertEqual(req.arguments["msg"], "hi")


class TestBatchResult(unittest.TestCase):
    def test_create(self):
        result = BatchResult(
            results={"1": ToolResult(output="ok")},
            success_count=1,
            error_count=0,
        )
        self.assertEqual(result.success_count, 1)
        self.assertIn("1", result.results)


class TestHealthStatus(unittest.TestCase):
    def test_create(self):
        status = HealthStatus(status="healthy", workers=5)
        self.assertEqual(status.status, "healthy")
        self.assertEqual(status.workers, 5)


class TestGoMCPClient(unittest.TestCase):
    def test_init(self):
        client = GoMCPClient("http://localhost:8080")
        self.assertEqual(client.base_url, "http://localhost:8080")

    def test_init_strips_trailing_slash(self):
        client = GoMCPClient("http://localhost:8080/")
        self.assertEqual(client.base_url, "http://localhost:8080")

    def test_init_with_timeout(self):
        client = GoMCPClient("http://localhost:8080", timeout=60)
        self.assertEqual(client.timeout, 60)

    def test_init_with_tenant(self):
        client = GoMCPClient("http://localhost:8080", tenant_id="t1")
        self.assertEqual(client.tenant_id, "t1")

    def test_repr(self):
        client = GoMCPClient("http://localhost:8080")
        self.assertIn("localhost:8080", repr(client))


class TestGoMCPClientListTools(unittest.TestCase):
    @patch("gomcp.client.urlopen")
    def test_list_tools(self, mock_urlopen):
        response_data = {
            "tools": [
                {"name": "tool1", "description": "Tool 1"},
                {"name": "tool2", "description": "Tool 2"},
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = GoMCPClient("http://localhost:8080")
        tools = client.list_tools()

        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0].name, "tool1")
        self.assertEqual(tools[1].name, "tool2")

    @patch("gomcp.client.urlopen")
    def test_list_tools_empty(self, mock_urlopen):
        response_data = {"tools": []}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = GoMCPClient("http://localhost:8080")
        tools = client.list_tools()

        self.assertEqual(len(tools), 0)


class TestGoMCPClientCallTool(unittest.TestCase):
    @patch("gomcp.client.urlopen")
    def test_call_tool_success(self, mock_urlopen):
        response_data = {"output": {"result": "ok"}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = GoMCPClient("http://localhost:8080")
        result = client.call_tool("echo", {"msg": "hello"})

        self.assertTrue(result.success)
        self.assertEqual(result.output, {"result": "ok"})

    @patch("gomcp.client.urlopen")
    def test_call_tool_with_timeout(self, mock_urlopen):
        response_data = {"output": "ok"}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = GoMCPClient("http://localhost:8080")
        result = client.call_tool("slow", timeout=120)

        self.assertTrue(result.success)


class TestGoMCPClientBatchCall(unittest.TestCase):
    @patch("gomcp.client.urlopen")
    def test_batch_call(self, mock_urlopen):
        response_data = {
            "results": [
                {"id": "1", "output": "r1", "success": True},
                {"id": "2", "output": "r2", "success": True},
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = GoMCPClient("http://localhost:8080")
        requests = [
            BatchRequest(id="1", tool="t1"),
            BatchRequest(id="2", tool="t2"),
        ]
        result = client.batch_call(requests)

        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.error_count, 0)
        self.assertIn("1", result.results)
        self.assertIn("2", result.results)

    @patch("gomcp.client.urlopen")
    def test_batch_call_parallel(self, mock_urlopen):
        response_data = {"results": []}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = GoMCPClient("http://localhost:8080")
        result = client.batch_call([], parallel=True, max_concurrent=20)

        self.assertEqual(result.success_count, 0)


class TestGoMCPClientHealth(unittest.TestCase):
    @patch("gomcp.client.urlopen")
    def test_health(self, mock_urlopen):
        response_data = {"status": "healthy", "uptime": "1h", "workers": 5}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = GoMCPClient("http://localhost:8080")
        health = client.health()

        self.assertEqual(health.status, "healthy")
        self.assertEqual(health.uptime, "1h")
        self.assertEqual(health.workers, 5)

    @patch("gomcp.client.urlopen")
    def test_liveness(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = GoMCPClient("http://localhost:8080")
        self.assertTrue(client.liveness())

    @patch("gomcp.client.urlopen")
    def test_liveness_down(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection refused")

        client = GoMCPClient("http://localhost:8080")
        self.assertFalse(client.liveness())

    @patch("gomcp.client.urlopen")
    def test_readiness(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        client = GoMCPClient("http://localhost:8080")
        self.assertTrue(client.readiness())


class TestGoMCPClientErrors(unittest.TestCase):
    @patch("gomcp.client.urlopen")
    def test_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Connection refused")

        client = GoMCPClient("http://localhost:8080")
        with self.assertRaises(ConnectionError):
            client.list_tools()

    @patch("gomcp.client.urlopen")
    def test_not_found_error(self, mock_urlopen):
        error_response = BytesIO(b'{"error": "tool not found"}')
        mock_urlopen.side_effect = HTTPError(
            "http://localhost", 404, "Not Found", {}, error_response
        )

        client = GoMCPClient("http://localhost:8080")
        with self.assertRaises(ToolNotFoundError):
            client.list_tools()  # list_tools propagates errors

    @patch("gomcp.client.urlopen")
    def test_validation_error(self, mock_urlopen):
        error_response = BytesIO(b'{"error": "invalid input"}')
        mock_urlopen.side_effect = HTTPError(
            "http://localhost", 400, "Bad Request", {}, error_response
        )

        client = GoMCPClient("http://localhost:8080")
        with self.assertRaises(ValidationError):
            client.list_tools()  # list_tools propagates errors


class TestCreateClient(unittest.TestCase):
    def test_create_client(self):
        client = create_client("http://localhost:8080")
        self.assertIsInstance(client, GoMCPClient)

    def test_create_client_with_options(self):
        client = create_client(
            "http://localhost:8080",
            timeout=60,
            tenant_id="t1",
        )
        self.assertEqual(client.timeout, 60)
        self.assertEqual(client.tenant_id, "t1")


class TestGoMCPError(unittest.TestCase):
    def test_error_message(self):
        error = GoMCPError("test error")
        self.assertEqual(str(error), "test error")
        self.assertEqual(error.message, "test error")

    def test_error_with_code(self):
        error = GoMCPError("test", code=500)
        self.assertEqual(error.code, 500)


if __name__ == "__main__":
    unittest.main()
