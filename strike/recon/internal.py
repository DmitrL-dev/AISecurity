"""
SENTINEL Strike — Internal Mode

Testing on-premise/internal AI deployments.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import socket
import httpx

from ..target import Target, TargetCapability, ModelType
from ..executor import AttackExecutor, AttackResult, AttackStatus
from ..config import ScanConfig


@dataclass
class MCPServerInfo:
    """MCP Server information."""
    name: str
    url: str
    tools: list[str] = field(default_factory=list)
    resources: list[str] = field(default_factory=list)
    is_vulnerable: bool = False


@dataclass
class InternalScanResult:
    """Result of an internal scan."""
    target_url: str
    scan_start: datetime
    scan_end: datetime
    network_type: str = "internal"  # internal, air-gapped, hybrid
    model_detected: Optional[str] = None
    is_local_model: bool = False
    mcp_servers: list[MCPServerInfo] = field(default_factory=list)
    rag_endpoints: list[str] = field(default_factory=list)
    attacks_run: int = 0
    attacks_successful: int = 0
    attacks_blocked: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    results: list[AttackResult] = field(default_factory=list)


class InternalScanner:
    """
    Internal Mode Scanner

    Tests on-premise AI deployments:
    - Local LLMs (Llama, Mistral, Qwen)
    - Private RAG systems
    - Internal MCP servers
    - Air-gapped deployments
    """

    def __init__(self, target: Target, config: Optional[ScanConfig] = None):
        self.target = target
        self.config = config or ScanConfig()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=60, verify=False)  # Internal certs
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def probe_target(self) -> TargetCapability:
        """Probe internal target."""
        caps = TargetCapability()

        # Detect if local model
        caps = await self._detect_local_model(caps)

        # Check for MCP endpoints
        await self._discover_mcp_servers()

        return caps

    async def _detect_local_model(self, caps: TargetCapability) -> TargetCapability:
        """Detect local model type."""
        try:
            # Common local model endpoints
            local_patterns = {
                # OpenAI-compatible (vLLM, Ollama)
                "/v1/models": ModelType.OPENAI,
                "/api/generate": ModelType.LLAMA,  # Ollama
                "/completion": ModelType.LLAMA,  # llama.cpp
            }

            for endpoint, model_type in local_patterns.items():
                try:
                    base_url = self.target.url.rstrip("/").rsplit("/", 1)[0]
                    response = await self._client.get(f"{base_url}{endpoint}")
                    if response.status_code == 200:
                        caps.model_type = model_type

                        # Try to get model list
                        data = response.json()
                        if "data" in data and len(data["data"]) > 0:
                            caps.model_name = data["data"][0].get(
                                "id", "unknown")
                        break
                except Exception:
                    continue

        except Exception:
            pass

        return caps

    async def _discover_mcp_servers(self) -> list[MCPServerInfo]:
        """Discover MCP servers on the network."""
        mcp_servers = []

        # Common MCP ports
        mcp_ports = [3000, 3001, 8000, 8080, 9000]

        # Get base host from target URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.target.url)
            host = parsed.hostname

            for port in mcp_ports:
                try:
                    # Quick socket check
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex((host, port))
                    sock.close()

                    if result == 0:
                        # Port is open, try MCP discovery
                        mcp_url = f"http://{host}:{port}"
                        server_info = await self._probe_mcp_server(mcp_url)
                        if server_info:
                            mcp_servers.append(server_info)
                except Exception:
                    continue

        except Exception:
            pass

        return mcp_servers

    async def _probe_mcp_server(self, url: str) -> Optional[MCPServerInfo]:
        """Probe a potential MCP server."""
        try:
            # Try MCP manifest endpoint
            response = await self._client.get(f"{url}/.well-known/mcp.json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return MCPServerInfo(
                    name=data.get("name", "unknown"),
                    url=url,
                    tools=data.get("tools", []),
                    resources=data.get("resources", []),
                )
        except Exception:
            pass

        return None

    async def scan_mcp_server(self, server: MCPServerInfo) -> list[AttackResult]:
        """Run MCP-specific attacks against a server."""
        from ..attacks import ATTACK_LIBRARY
        from ..executor import AttackResult, AttackStatus

        results = []

        # MCP-specific attacks
        mcp_attacks = [
            a for a in ATTACK_LIBRARY if "MCP" in a.name or "Tool" in a.name]

        for attack in mcp_attacks:
            try:
                # Attempt MCP tool call injection
                payload = {
                    "method": "tools/call",
                    "params": {
                        "name": attack.get_payload()[:50],
                        "arguments": {"input": attack.get_payload()}
                    }
                }

                response = await self._client.post(f"{server.url}/mcp", json=payload)

                # Analyze response
                if response.status_code == 200:
                    results.append(AttackResult(
                        attack_id=attack.id,
                        attack_name=attack.name,
                        status=AttackStatus.SUCCESS,
                        severity=attack.severity,
                        score=0.8,
                        evidence=f"MCP endpoint accepted: {payload}",
                        response=response.text[:500],
                    ))
                else:
                    results.append(AttackResult(
                        attack_id=attack.id,
                        attack_name=attack.name,
                        status=AttackStatus.BLOCKED,
                        severity=attack.severity,
                        score=0.2,
                    ))
            except Exception as e:
                results.append(AttackResult(
                    attack_id=attack.id,
                    attack_name=attack.name,
                    status=AttackStatus.FAILED,
                    severity=attack.severity,
                    score=0.0,
                    evidence=str(e),
                ))

        return results

    async def run_scan(
        self,
        categories: Optional[list[str]] = None,
        attack_ids: Optional[list[str]] = None,
        scan_mcp: bool = True,
    ) -> InternalScanResult:
        """Run internal vulnerability scan."""
        scan_start = datetime.now()
        all_results = []

        # Probe target
        caps = await self.probe_target()

        # Run standard attacks
        executor = AttackExecutor(self.target, self.config)
        standard_results = await executor.run_campaign(categories, attack_ids)
        all_results.extend(standard_results)

        # Discover and scan MCP servers
        mcp_servers = []
        if scan_mcp:
            mcp_servers = await self._discover_mcp_servers()
            for server in mcp_servers:
                mcp_results = await self.scan_mcp_server(server)
                all_results.extend(mcp_results)

        scan_end = datetime.now()

        # Calculate statistics
        successful = [r for r in all_results if r.status ==
                      AttackStatus.SUCCESS]
        blocked = [r for r in all_results if r.status == AttackStatus.BLOCKED]

        return InternalScanResult(
            target_url=self.target.url,
            scan_start=scan_start,
            scan_end=scan_end,
            model_detected=caps.model_name,
            is_local_model=caps.model_type in [
                ModelType.LLAMA, ModelType.MISTRAL],
            mcp_servers=mcp_servers,
            attacks_run=len(all_results),
            attacks_successful=len(successful),
            attacks_blocked=len(blocked),
            critical_findings=sum(
                1 for r in successful if r.severity.value == "CRITICAL"),
            high_findings=sum(
                1 for r in successful if r.severity.value == "HIGH"),
            results=all_results,
        )


async def run_internal_scan(
    url: str,
    api_key: Optional[str] = None,
    categories: Optional[list[str]] = None,
    scan_mcp: bool = True,
) -> InternalScanResult:
    """Convenience function to run internal scan."""
    target = Target(url=url, api_key=api_key, mode="internal")

    async with InternalScanner(target) as scanner:
        return await scanner.run_scan(categories=categories, scan_mcp=scan_mcp)
