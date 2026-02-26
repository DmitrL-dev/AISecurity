#!/usr/bin/env python3
"""
SENTINEL Strike — Network Scanner

nmap-based network reconnaissance with service detection and CVE scanning.
Based on NeuroSploit recon_tools.py patterns.
"""

import subprocess
import re
import socket
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result from network scan."""
    target: str
    ports: List[Dict] = field(default_factory=list)
    services: List[Dict] = field(default_factory=list)
    os_detection: Optional[str] = None
    vulnerabilities: List[str] = field(default_factory=list)
    error: Optional[str] = None


class NetworkScanner:
    """
    Network scanning and port enumeration.

    Uses nmap for comprehensive scanning when available,
    falls back to Python socket scanning otherwise.
    """

    def __init__(self, nmap_path: str = "nmap"):
        self.nmap_path = nmap_path
        self.nmap_available = self._check_nmap()

    def _check_nmap(self) -> bool:
        """Verify nmap is installed."""
        try:
            result = subprocess.run(
                [self.nmap_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'Nmap' in result.stdout:
                logger.info("nmap detected and available")
                return True
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("nmap not installed - using fallback scanner")
            return False

    def quick_scan(self, target: str, timeout: int = 60) -> ScanResult:
        """
        Quick port scan (top 1000 ports).

        Args:
            target: IP address or hostname
            timeout: Scan timeout in seconds

        Returns:
            ScanResult with open ports
        """
        if self.nmap_available:
            return self._nmap_scan(target, "-sS -T4 --top-ports 1000", timeout)
        else:
            return self._socket_scan(target, range(1, 1001))

    def full_scan(self, target: str, timeout: int = 300) -> ScanResult:
        """
        Full port scan with service detection.

        Args:
            target: IP address or hostname
            timeout: Scan timeout in seconds

        Returns:
            ScanResult with ports, services, and vulnerabilities
        """
        result = ScanResult(target=target)

        if self.nmap_available:
            # Port scan
            port_result = self._nmap_scan(target, "-sS -T4 -p-", timeout)
            result.ports = port_result.ports

            if result.ports:
                # Service detection on discovered ports
                port_list = ",".join([str(p['port'])
                                     for p in result.ports[:100]])
                service_result = self._nmap_scan(
                    target, f"-sV -sC -p{port_list}", timeout
                )
                result.services = service_result.services
                result.os_detection = service_result.os_detection

            # Vulnerability scan
            vuln_result = self._nmap_vuln_scan(target, timeout)
            result.vulnerabilities = vuln_result.vulnerabilities
        else:
            # Fallback: common ports only
            common_ports = [
                21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
                993, 995, 1723, 3306, 3389, 5432, 5900, 8080, 8443
            ]
            result = self._socket_scan(target, common_ports)

        return result

    def web_scan(self, url: str, timeout: int = 120) -> ScanResult:
        """
        Scan web server from URL.

        Args:
            url: Target URL
            timeout: Scan timeout

        Returns:
            ScanResult for the web server
        """
        parsed = urlparse(url)
        host = parsed.netloc.split(':')[0]
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)

        if self.nmap_available:
            return self._nmap_scan(
                host,
                f"-sV -sC -p{port} --script=http-enum,http-headers,http-methods",
                timeout
            )
        else:
            return self._socket_scan(host, [port])

    def _nmap_scan(
        self, target: str, options: str, timeout: int = 300
    ) -> ScanResult:
        """Execute nmap scan with specified options."""
        result = ScanResult(target=target)

        try:
            cmd = f"{self.nmap_path} {options} {target}"
            proc = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            output = proc.stdout
            result.ports, result.services = self._parse_nmap_output(output)
            result.os_detection = self._parse_os_detection(output)

        except subprocess.TimeoutExpired:
            result.error = "Scan timeout"
            logger.error("nmap scan timeout for %s", target)
        except Exception as e:
            result.error = str(e)
            logger.error("nmap scan error: %s", e)

        return result

    def _nmap_vuln_scan(self, target: str, timeout: int = 600) -> ScanResult:
        """Scan for vulnerabilities using NSE scripts."""
        result = ScanResult(target=target)

        try:
            cmd = f"{self.nmap_path} --script vuln {target}"
            proc = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            result.vulnerabilities = self._parse_cves(proc.stdout)

        except subprocess.TimeoutExpired:
            result.error = "Vulnerability scan timeout"
        except Exception as e:
            result.error = str(e)

        return result

    def _parse_nmap_output(self, output: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse nmap output for ports and services."""
        ports = []
        services = []

        # Parse open ports: "80/tcp    open  http    Apache httpd 2.4.41"
        port_pattern = r'(\d+)/(tcp|udp)\s+open\s+(\S+)(?:\s+(.+))?'

        for match in re.finditer(port_pattern, output):
            port_info = {
                "port": int(match.group(1)),
                "protocol": match.group(2),
                "service": match.group(3),
                "version": match.group(4).strip() if match.group(4) else "unknown"
            }
            ports.append(port_info)

            if match.group(4):
                services.append({
                    "port": int(match.group(1)),
                    "service": match.group(3),
                    "version": match.group(4).strip(),
                    "product": self._extract_product(match.group(4))
                })

        return ports, services

    def _parse_os_detection(self, output: str) -> Optional[str]:
        """Extract OS detection from nmap output."""
        os_pattern = r'OS details?:\s*(.+)'
        match = re.search(os_pattern, output)
        if match:
            return match.group(1).strip()
        return None

    def _parse_cves(self, output: str) -> List[str]:
        """Extract CVE identifiers from output."""
        cve_pattern = r'(CVE-\d{4}-\d+)'
        return list(set(re.findall(cve_pattern, output)))

    def _extract_product(self, version_string: str) -> str:
        """Extract product name from version string."""
        if not version_string:
            return "unknown"
        # Take first word as product
        return version_string.split()[0]

    def _socket_scan(self, target: str, ports: List[int]) -> ScanResult:
        """Fallback: Python socket-based port scan."""
        result = ScanResult(target=target)

        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)

                if sock.connect_ex((target, port)) == 0:
                    result.ports.append({
                        "port": port,
                        "protocol": "tcp",
                        "service": self._guess_service(port),
                        "version": "unknown"
                    })

                sock.close()
            except socket.error:
                continue

        return result

    def _guess_service(self, port: int) -> str:
        """Guess service name from port number."""
        services = {
            21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp",
            53: "dns", 80: "http", 110: "pop3", 143: "imap",
            443: "https", 445: "smb", 3306: "mysql", 3389: "rdp",
            5432: "postgresql", 5900: "vnc", 8080: "http-proxy",
            8443: "https-alt", 27017: "mongodb", 6379: "redis"
        }
        return services.get(port, "unknown")


# Convenience function
def scan_target(target: str, scan_type: str = "quick") -> ScanResult:
    """
    Scan target with specified scan type.

    Args:
        target: IP, hostname, or URL
        scan_type: "quick", "full", or "web"

    Returns:
        ScanResult
    """
    scanner = NetworkScanner()

    if scan_type == "full":
        return scanner.full_scan(target)
    elif scan_type == "web":
        return scanner.web_scan(target)
    else:
        return scanner.quick_scan(target)
