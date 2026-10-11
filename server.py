"""
SQLWeb — The Web Server Nobody Asked For.

Developed by The Mad Tech Head and his faithful assistant Igor.

Python handles HTTP transport.
SQLite handles response selection.

The engineering justification remains unresolved.
"""

import argparse
import sqlite3

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent

SCHEMA_SQL = (
    ROOT / "sql" / "schema.sql"
).read_text(encoding="utf-8")

DISPATCH_SQL = (
    ROOT / "sql" / "dispatch.sql"
).read_text(encoding="utf-8")


MIDDLEWARE_SCHEMA_SQL = (
    ROOT / "sql" / "middleware_schema.sql"
).read_text(encoding="utf-8")

MIDDLEWARE_DISPATCH_SQL = (
    ROOT / "sql" / "middleware_dispatch.sql"
).read_text(encoding="utf-8")


def initialize_database(database_path):
    """Create the database and seed default routes."""

    with sqlite3.connect(database_path) as connection:
        connection.executescript(SCHEMA_SQL)
        connection.executescript(MIDDLEWARE_SCHEMA_SQL)


def make_handler(database_path):
    """Create an HTTP handler using SQL for response selection."""

    database_path = Path(database_path).resolve()

    class SQLWebHandler(BaseHTTPRequestHandler):

        server_version = "SQLWeb/0.2"

        def do_GET(self):
            """Process an HTTP GET request through SQLite."""

            path = urlsplit(self.path).path

            try:
                with sqlite3.connect(
                    database_path,
                    timeout=5.0,
                ) as connection:

                    decision = connection.execute(
                        MIDDLEWARE_DISPATCH_SQL,
                        {
                            "method": "GET",
                            "path": path,
                        },
                    ).fetchone()

                    if decision is None:
                        raise RuntimeError(
                            "Middleware returned no decision"
                        )

                    action, mw_status, mw_type, mw_body = decision

                    if action == "DENY":
                        result = (
                            mw_status,
                            mw_type,
                            mw_body,
                        )
                    elif action == "ALLOW":
                        result = connection.execute(
                            DISPATCH_SQL,
                            {
                                "method": "GET",
                                "path": path,
                            },
                        ).fetchone()
                    else:
                        raise RuntimeError(
                            "Unsupported middleware action"
                        )

                if result is None:
                    raise RuntimeError(
                        "SQL dispatcher returned no response"
                    )

                status, content_type, body = result

                payload = body.encode("utf-8")

            except (
                sqlite3.Error,
                RuntimeError,
                UnicodeError,
            ) as error:

                self.log_error(
                    "SQL dispatch failure: %s",
                    error,
                )

                status = 500
                content_type = "text/plain; charset=utf-8"
                payload = b"500: Igor has encountered a complication."

            self.send_response(status)

            self.send_header(
                "Content-Type",
                content_type,
            )

            self.send_header(
                "Content-Length",
                str(len(payload)),
            )

            self.send_header(
                "X-Powered-By",
                "Questionable Engineering Decisions",
            )

            self.end_headers()

            self.wfile.write(payload)

        def do_HEAD(self):
            """Reject unsupported HEAD requests."""

            self.send_response(405)
            self.send_header("Allow", "GET")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self):
            """Reject unsupported POST requests."""

            self.send_response(405)
            self.send_header("Allow", "GET")
            self.send_header("Content-Length", "0")
            self.end_headers()

    return SQLWebHandler


def main():
    """Start the SQL-powered HTTP server."""

    parser = argparse.ArgumentParser(
        description="SQLWeb — A Questionable Achievement"
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8080,
    )

    args = parser.parse_args()

    database_path = ROOT / "sqlweb.db"

    initialize_database(database_path)

    server = ThreadingHTTPServer(
        (args.host, args.port),
        make_handler(database_path),
    )

    print(
        f"SQLWeb listening at "
        f"http://{args.host}:{server.server_port}",
        flush=True,
    )

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print(
            "\nIgor: Shutting down, Master.",
            flush=True,
        )

    finally:
        server.server_close()


if __name__ == "__main__":
    main()
