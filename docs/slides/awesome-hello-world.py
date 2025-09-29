#!/nix/store/qfcbvbm2wzpgh2m1j5b8yd61y8y8x5nw-isd-tui-env/bin/python
import http.server
import time
import sys
import random

PORT = 8181


class HelloHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Hello World!".encode("utf-8"))


def log_debug():
    print(
        f"{time.ctime()} DEBUG: heartbeat",
        file=sys.stderr,
        flush=True,
    )


def log_log():
    print(
        f"{time.ctime()} LOG: logging something interesting...",
        file=sys.stderr,
        flush=True,
    )


if __name__ == "__main__":
    # Start background noisy logger
    # add some noisy output
    for _ in range(30):
        r = random.randint(0, 1)
        if r == 0:
            log_debug()
        if r == 2:
            log_log()

    try:
        import socketserver

        with socketserver.TCPServer(("", PORT), HelloHandler) as httpd:
            # print(f"Serving on port {PORT}, reading from {HELLO_FILE}", flush=True)
            httpd.serve_forever()
    except Exception as e:
        # simulate shutting down
        print(
            f"{time.ctime()} ERROR: {e}",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"{time.ctime()} STOPPING: shutting down with delay",
            file=sys.stderr,
            flush=True,
        )
        for _ in range(20):
            log_debug()

        exit(1)
