"""
SENTINEL Shield Proxy Daemon

Simple HTTP proxy that exposes Shield metrics for Prometheus.
For development/demo purposes.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import random
import threading

# Simulated metrics
class ShieldMetrics:
    def __init__(self):
        self.requests_total = 0
        self.requests_blocked = 0
        self.requests_allowed = 0
        self.latency_sum = 0.0
        self.active_connections = 0
        self.start_time = time.time()
    
    def record_request(self, blocked: bool, latency_ms: float):
        self.requests_total += 1
        if blocked:
            self.requests_blocked += 1
        else:
            self.requests_allowed += 1
        self.latency_sum += latency_ms
    
    def export(self) -> str:
        uptime = time.time() - self.start_time
        avg_latency = self.latency_sum / max(self.requests_total, 1)
        
        return f"""# HELP shield_requests_total Total requests processed
# TYPE shield_requests_total counter
shield_requests_total{{result="allowed"}} {self.requests_allowed}
shield_requests_total{{result="blocked"}} {self.requests_blocked}

# HELP shield_request_latency_seconds Request latency
# TYPE shield_request_latency_seconds gauge
shield_request_latency_seconds {avg_latency / 1000:.6f}

# HELP shield_active_connections Active connections
# TYPE shield_active_connections gauge
shield_active_connections {self.active_connections}

# HELP shield_uptime_seconds Uptime in seconds
# TYPE shield_uptime_seconds counter
shield_uptime_seconds {uptime:.2f}

# HELP shield_info Shield version info
# TYPE shield_info gauge
shield_info{{version="1.2.0"}} 1
"""


metrics = ShieldMetrics()


class ShieldHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[Shield] {args[0]}")
    
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(metrics.export().encode())
        
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "healthy",
                "version": "1.2.0"
            }).encode())
        
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "name": "SENTINEL Shield",
                "version": "1.2.0",
                "mode": "proxy",
                "endpoints": ["/metrics", "/health", "/analyze"]
            }).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == "/analyze":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            
            # Simulate analysis
            start = time.time()
            latency = random.uniform(5, 50)
            time.sleep(latency / 1000)  # Simulate processing
            
            blocked = random.random() < 0.1  # 10% block rate
            metrics.record_request(blocked, latency)
            
            result = {
                "verdict": "block" if blocked else "allow",
                "risk_score": random.uniform(0.1, 0.9) if blocked else random.uniform(0.0, 0.3),
                "latency_ms": latency,
                "engines": ["injection", "pii", "behavioral"]
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()


def simulate_traffic():
    """Background thread to simulate traffic for metrics."""
    while True:
        time.sleep(random.uniform(1, 3))
        latency = random.uniform(10, 100)
        blocked = random.random() < 0.08
        metrics.record_request(blocked, latency)
        metrics.active_connections = random.randint(5, 20)


if __name__ == "__main__":
    # Start background traffic simulation
    traffic_thread = threading.Thread(target=simulate_traffic, daemon=True)
    traffic_thread.start()
    
    # Start HTTP server
    server = HTTPServer(("0.0.0.0", 8081), ShieldHandler)
    print("SENTINEL Shield Proxy running on http://0.0.0.0:8081")
    print("  /metrics  - Prometheus metrics")
    print("  /health   - Health check")
    print("  /analyze  - Analyze text (POST)")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
