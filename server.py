"""SQLWeb — The Web Server Nobody Asked For.

Developed by The Mad Tech Head and his faithful assistant Igor.
"""

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class SQLWebHandler(BaseHTTPRequestHandler):
    """Minimal HTTP transport adapter."""

    server_version = "SQLWeb/0.1"

    def do_GET(self):
        """Return the initial HTTP response."""

        body = (
            "SQLWeb — The Web Server Nobody Asked For\n"
            "Developed by The Mad Tech Head and Igor.\n"
            "The SQL engine is not connected yet.\n"
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="SQLWeb HTTP transport")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    server = ThreadingHTTPServer(
        (args.host, args.port),
        SQLWebHandler,
    )

    print(
        f"SQLWeb listening at http://{args.host}:{server.server_port}",
        flush=True,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
