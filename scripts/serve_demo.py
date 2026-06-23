"""Minimal HTTP health server + CLI demo runner for Render web service."""
import http.server
import json
import os
import sys
import threading
import time
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

PORT = int(os.environ.get("PORT", "10000"))


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "service": "dispatchmind-cli"}).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write("DispatchMind CLI Demo - see Render logs for output".encode())

    def log_message(self, format, *args):
        pass  # suppress HTTP log noise


def run_health_server():
    server = http.server.HTTPServer(("0.0.0.0", PORT), HealthHandler)
    server.serve_forever()


def main():
    # Start health server in background
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()
    print(f"[serve] Health server on 0.0.0.0:{PORT}")

    # Run CLI demo
    import scripts.cli_demo as cli_demo
    cli_demo.main()

    # Keep running so Render doesn't restart
    print(f"[serve] CLI demo complete. Health server stays up on :{PORT}")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
