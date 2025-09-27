#!/usr/bin/env python3
import http.server
import socketserver
import time
import threading
import sys
import random
from pathlib import Path

PORT = 8181
HELLO_FILE = Path("/opt/hello/hello.txt")


class HelloHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        time.sleep(5)
        try:
            text = HELLO_FILE.read_text()
        except Exception as e:
            text = f"ERROR: cannot read {HELLO_FILE}: {e}"
        self.wfile.write(text.encode("utf-8"))


def noisy_logger():
    """Generate noisy logs forever"""
    while True:
        r = random.randint(0, 2)
        if r == 0:
            print(
                f"{time.ctime()} DEBUG: heartbeat from awesome-hello-world",
                file=sys.stderr,
                flush=True,
            )
        elif r == 1:
            print(
                f"{time.ctime()} WARN: pretending to have triggered an warning in awesome-hello-world",
                file=sys.stderr,
                flush=True,
            )
        else:
            print(
                f"{time.ctime()} LOG: pretending to log in awesome-hello-world",
                file=sys.stderr,
                flush=True,
            )

        time.sleep(0.5)


if __name__ == "__main__":
    # Start background noisy logger
    threading.Thread(target=noisy_logger, daemon=True).start()

    with socketserver.TCPServer(("", PORT), HelloHandler) as httpd:
        # print(f"Serving on port {PORT}, reading from {HELLO_FILE}", flush=True)
        httpd.serve_forever()
