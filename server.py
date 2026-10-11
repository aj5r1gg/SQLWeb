"""SQLWeb: SQL decides; Python transports."""

import argparse
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
ROUTES = (ROOT / "sql/schema.sql").read_text(encoding="utf-8")
MIDDLEWARE = (ROOT / "sql/middleware_schema.sql").read_text(
    encoding="utf-8"
)
REQUEST_PIPELINE_SQL = (ROOT / "sql/request_pipeline.sql").read_text(
    encoding="utf-8"
)


REQUEST_PIPELINE_V2_SQL = (
    ROOT / "sql/request_pipeline_v2.sql"
).read_text(encoding="utf-8")


def middleware_fingerprint(db):
    """Fingerprint the application's middleware table and index."""
    return db.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_schema
        WHERE name IN (
            'middleware_rules',
            'middleware_rules_lookup'
        )
        ORDER BY type, name
        """
    ).fetchall()


def expected_middleware_fingerprints():
    """Construct canonical fingerprints from shipped SQL."""
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(MIDDLEWARE)
        legacy = middleware_fingerprint(db)

        migration = (
            ROOT / "sql/middleware_upgrade_v2.sql"
        ).read_text(encoding="utf-8")

        db.executescript(migration)
        upgraded = middleware_fingerprint(db)

    if len(legacy) != 2 or len(upgraded) != 2:
        raise ValueError("Invalid canonical middleware schemas")

    if legacy == upgraded:
        raise ValueError("Middleware versions are indistinguishable")

    return legacy, upgraded


LEGACY_FINGERPRINT, V2_FINGERPRINT = (
    expected_middleware_fingerprints()
)


def select_request_pipeline(db):
    """Select the SQL pipeline from a verified schema definition."""
    actual = middleware_fingerprint(db)

    if actual == LEGACY_FINGERPRINT:
        return REQUEST_PIPELINE_SQL

    if actual == V2_FINGERPRINT:
        return REQUEST_PIPELINE_V2_SQL

    raise ValueError("Unsupported middleware schema")



def initialize_database(path, *, middleware_version=2):
    """Create v2 by default; preserve existing middleware versions."""
    if middleware_version not in (1, 2):
        raise ValueError("Unsupported middleware version")

    with closing(sqlite3.connect(path)) as db:
        existing = db.execute(
            """
            SELECT 1 FROM sqlite_schema
            WHERE type = 'table' AND name = 'middleware_rules'
            """
        ).fetchone() is not None

        if existing:
            select_request_pipeline(db)
            db.executescript(ROUTES)
            return

        db.executescript(ROUTES)
        db.executescript(MIDDLEWARE)

        if middleware_version == 2:
            migration = (
                ROOT / "sql/middleware_upgrade_v2.sql"
            ).read_text(encoding="utf-8")
            db.executescript(migration)

        select_request_pipeline(db)


def make_handler(database_path):
    database_path = Path(database_path).resolve()

    class Handler(BaseHTTPRequestHandler):
        server_version = "SQLWeb/0.2"

        def do_GET(self):
            try:
                with closing(sqlite3.connect(
                    database_path, timeout=5.0
                )) as db:
                    pipeline = select_request_pipeline(db)
                    response = db.execute(
                        pipeline,
                        {
                            "method": self.command,
                            "path": urlsplit(self.path).path,
                        },
                    ).fetchone()

                if response is None or len(response) != 7:
                    raise ValueError("Invalid SQL response")

                _, status, content_type, body, location, _, allow = response

                if type(status) is not int or not 200 <= status <= 599:
                    raise ValueError("Invalid HTTP status")
                if not isinstance(content_type, str):
                    raise ValueError("Invalid content type")
                if not content_type or any(
                    c in content_type for c in "\r\n\0"
                ):
                    raise ValueError("Unsafe content type")
                if not isinstance(body, str):
                    raise ValueError("Invalid response body")

                if allow is not None:
                    if not isinstance(allow, str) or not allow:
                        raise ValueError("Invalid Allow header")
                    if any(c in allow for c in "\r\n\0"):
                        raise ValueError("Unsafe Allow header")

                if location is not None and status not in (
                    301, 302, 303, 307, 308
                ):
                    raise ValueError("Unexpected Location header")

                if status in (301, 302, 303, 307, 308):
                    if location is None:
                        raise ValueError("Missing redirect Location")

                if location is not None:
                    if not isinstance(location, str):
                        raise ValueError("Invalid Location header")
                    if (
                        not 1 <= len(location) <= 512
                        or not location.startswith("/")
                        or location.startswith("//")
                        or not location.isascii()
                        or any(
                            c not in
                            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                            "abcdefghijklmnopqrstuvwxyz"
                            "0123456789/_~-."
                            for c in location
                        )
                    ):
                        raise ValueError("Unsafe Location header")

                payload = body.encode("utf-8")

            except (sqlite3.Error, ValueError, TypeError,
                    UnicodeError) as error:
                self.log_error("SQL dispatch failure: %s", error)
                status = 500
                allow = None
                location = None
                content_type = "text/plain; charset=utf-8"
                payload = b"500: Igor has encountered a complication."

            self.send_response(status)
            if allow is not None:
                self.send_header("Allow", allow)
            if location is not None:
                self.send_header("Location", location)
            if self.command == "POST":
                self.close_connection = True
                self.send_header("Connection", "close")
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header(
                "X-Powered-By", "Questionable Engineering Decisions"
            )
            self.end_headers()

            if self.command != "HEAD":
                self.wfile.write(payload)

        do_HEAD = do_GET
        do_POST = do_GET

    return Handler


def main():
    parser = argparse.ArgumentParser(
        description="SQLWeb — A Questionable Achievement"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    database = ROOT / "sqlweb.db"
    initialize_database(database)

    with ThreadingHTTPServer(
        (args.host, args.port), make_handler(database)
    ) as server:
        print(
            f"SQLWeb listening at "
            f"http://{args.host}:{server.server_port}",
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nIgor: Shutting down, Master.", flush=True)


if __name__ == "__main__":
    main()
