"""SQLWeb HTTP integration regression tests."""

import sqlite3
import tempfile
import threading
import unittest

from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import initialize_database, make_handler


class SQLWebIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.database_path = (
            Path(cls.temporary_directory.name) / "test.db"
        )

        initialize_database(cls.database_path)

        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            make_handler(cls.database_path),
        )

        cls.thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls.thread.start()

        cls.base_url = (
            f"http://127.0.0.1:{cls.server.server_port}"
        )

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temporary_directory.cleanup()

    def test_homepage(self):
        with urlopen(self.base_url + "/", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"SQLWeb", response.read())

    def test_health(self):
        with urlopen(
            self.base_url + "/health", timeout=5
        ) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(
                response.headers.get_content_type(),
                "application/json",
            )
            self.assertIn(b'"status":"ok"', response.read())

    def test_igor(self):
        with urlopen(
            self.base_url + "/igor", timeout=5
        ) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(
                b"Unfortunately, it works",
                response.read(),
            )

    def test_missing_route(self):
        with self.assertRaises(HTTPError) as result:
            urlopen(
                self.base_url + "/missing", timeout=5
            )

        self.assertEqual(result.exception.code, 404)
        result.exception.close()

    def test_query_string(self):
        with urlopen(
            self.base_url + "/health?master=mad",
            timeout=5,
        ) as response:
            self.assertEqual(response.status, 200)

    def test_dynamic_route(self):
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO routes
                    (method, path, status, content_type, body)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "GET",
                    "/dynamic",
                    201,
                    "text/plain; charset=utf-8",
                    "SQLite is in charge.",
                ),
            )

        with urlopen(
            self.base_url + "/dynamic", timeout=5
        ) as response:
            self.assertEqual(response.status, 201)
            self.assertEqual(
                response.read(),
                b"SQLite is in charge.",
            )

    def test_post_rejected(self):
        request = Request(
            self.base_url + "/",
            data=b"test",
            method="POST",
        )

        with self.assertRaises(HTTPError) as result:
            urlopen(request, timeout=5)

        self.assertEqual(result.exception.code, 405)
        self.assertEqual(
            result.exception.headers.get("Allow"),
            "GET",
        )
        result.exception.close()

    def test_head_rejected(self):
        request = Request(
            self.base_url + "/",
            method="HEAD",
        )

        with self.assertRaises(HTTPError) as result:
            urlopen(request, timeout=5)

        self.assertEqual(result.exception.code, 405)
        self.assertEqual(
            result.exception.headers.get("Allow"),
            "GET",
        )
        result.exception.close()


if __name__ == "__main__":
    unittest.main()
