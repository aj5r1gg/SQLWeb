# SQLWeb

**The Web Server Nobody Asked For™**

*Because writing a web server in Assembly was far too sensible.*

SQLWeb is an experimental SQL-powered HTTP server. It uses SQLite to select HTTP routes, response status codes, content types and response bodies, while a small Python standard-library adapter handles the network transport.

Yes, it actually works.

No, that does not make it a sensible engineering decision.

## The Engineering Team

**The Mad Tech Head** — Chief Architect, Supreme Instigator of Questionable Engineering Decisions, and the man who looked at SQL and thought, "That could be a web server."

**Igor** — Faithful Assistant, Reluctant Voice of Reason, Keeper of the Unit Tests, and Accomplice in Crimes Against Software Architecture.

### How It Started

**Mad Tech Head:** "Igor! Can we build a web server using SQL?"

**Igor:** "Master, that is a spectacularly stupid idea."

**Mad Tech Head:** "Excellent! Start the repository."

**Igor:** "Very good, Master. Shall I prepare the unit tests?"

**Mad Tech Head:** "Obviously. We're not animals."

## Official Disclaimer

**WARNING: This project is not a parody implementation. It actually works. The parody is that we thought building it was a good idea.**

SQLWeb is a functioning experimental implementation, not a production-ready HTTP server. Its implementation is real; its architectural judgement remains under investigation.

**Just because you shouldn't doesn't mean we won't.**

## Features

- Functioning local HTTP listener.
- SQLite-backed route definitions.
- Parameterised SQL request dispatch.
- SQL-selected HTTP status codes, content types and response bodies.
- Persistent route database.
- Dynamic route additions without restarting the HTTP server.
- SQL-generated HTTP 404 responses.
- HTTP 405 responses for unsupported HEAD and POST methods.
- Eight HTTP integration regression tests.
- GitHub Actions continuous integration workflow.
- No third-party Python runtime dependencies.

## Requirements

Python 3.10 or newer, with SQLite support through the standard library.

No pip installation is required.

A questionable sense of humour is recommended.

## Quick Start

Clone the repository:

`git clone https://github.com/aj5r1gg/SQLWeb.git`

`cd SQLWeb`

Start SQLWeb:

`python3 server.py`

By default, SQLWeb listens at `http://127.0.0.1:8080`.

Try the following requests in another terminal:

- `curl -i http://127.0.0.1:8080/`
- `curl -i http://127.0.0.1:8080/health`
- `curl -i http://127.0.0.1:8080/igor`
- `curl -i http://127.0.0.1:8080/missing`

Stop the server using Ctrl+C.

### Default Endpoints

| Method | Path | Result |
|---|---|---|
| GET | `/` | HTTP 200 — SQLWeb introduction |
| GET | `/health` | HTTP 200 — JSON response |
| GET | `/igor` | HTTP 200 — Igor acknowledges the Master |
| GET | Unknown path | HTTP 404 |
| POST | Any path | HTTP 405 |
| HEAD | Any path | HTTP 405 |

The `/igor` endpoint returns:

**Yes, Master. Unfortunately, it works.**

## Architecture

SQLWeb's request flow is:

**HTTP client → Python HTTP adapter → SQLite → SQL dispatcher → Routes table → Python HTTP adapter → HTTP client**

Python handles TCP connections, HTTP parsing, response framing and network I/O.

SQLite handles route matching, status selection, content-type selection and response-body selection.

The primary implementation files are:

- `server.py` — HTTP transport and database integration.
- `sql/schema.sql` — SQLite route schema and default routes.
- `sql/dispatch.sql` — SQL-powered request dispatcher.
- `tests/test_sqlweb.py` — HTTP integration regression tests.

### Technical Honesty

SQLWeb v0.1 is an **SQL-powered HTTP server**, not a pure-SQL TCP/IP implementation.

SQL does not directly open sockets or implement network protocols in this release.

Even Igor has standards.

## Adding a Route

Start SQLWeb once to initialise `sqlweb.db`.

You can then insert routes through SQLite. For example, using the SQLite command-line client:

`sqlite3 sqlweb.db`

Execute the following SQL:

`INSERT INTO routes (method, path, status, content_type, body) VALUES ('GET', '/hello', 200, 'text/plain; charset=utf-8', 'Hello from SQLWeb!');`

Exit SQLite with `.quit`.

Request the new endpoint:

`curl -i http://127.0.0.1:8080/hello`

The server reads committed route changes from SQLite when requests arrive, so a restart is not required.

## Automated Testing

Run:

`python3 -m unittest discover -s tests -v`

The permanent regression suite covers the homepage, JSON health response, Igor endpoint, unknown routes, query strings, dynamic routes, POST rejection and HEAD rejection.

Tests use an isolated temporary database and a real local HTTP listener.

The GitHub Actions workflow runs these tests on pushes and pull requests. A successful local test run does not establish that remote CI has passed.

## Security

SQLWeb v0.1 is strictly an experimental development server. It binds to `127.0.0.1` by default.

It does not provide TLS termination, authentication, authorisation, rate limiting, comprehensive resource limits, or production-grade HTTP hardening.

**Do not expose SQLWeb v0.1 directly to the public internet.**

Publishing the source repository publicly is fine. Running the experimental server as a publicly accessible service is not recommended.

## Roadmap Nobody Requested

- [x] Build a working HTTP server.
- [x] Implement SQLite-backed routing.
- [x] Generate HTTP responses selected by SQL.
- [x] Add dynamically modifiable routes.
- [x] Introduce Igor.
- [x] Add permanent HTTP integration tests.
- [x] Configure GitHub Actions.
- [ ] SQL-defined middleware.
- [ ] SQL-generated custom error pages.
- [ ] SQL-defined response headers.
- [ ] SQL-based request logging.
- [ ] HTTP profiling using `EXPLAIN QUERY PLAN`.
- [ ] Comparative benchmarks against conventional HTTP servers.
- [ ] SQL-based template rendering.
- [ ] Discover how much more ridiculous this can become.

**Rejected feature:** An ORM to avoid writing SQL. Igor considers this philosophically indefensible.

## Frequently Asked Questions

**Is this a good idea?**

No.

**Does it actually work?**

Yes.

**Why SQL?**

Because Assembly was already taken.

**Is it production-ready?**

Absolutely not.

**Is this a joke?**

The engineering decision is a joke. The implementation is real.

**Who is responsible?**

The Mad Tech Head. Igor wishes to clarify that he was following instructions.

**Will SQLWeb outperform Nginx?**

No such claim has been made. No comparative benchmark has been performed.

**Can I contribute?**

Certainly. Pull requests should include tests, bug reports should contain reproducible steps, and architectural proposals should preferably involve SQL in some entirely unnecessary capacity.

**Will there be a version 0.2?**

Regrettably, probably.

## Development Philosophy

1. The implementation must actually work.
2. Tests must verify meaningful behaviour.
3. Technical claims must be accurate.
4. Deliberately absurd architecture is encouraged.
5. Deliberately broken software is not.
6. Security limitations must be documented.
7. Benchmark results must never be invented.
8. Igor is permitted to object.
9. The Mad Tech Head is permitted to ignore Igor.
10. Both remain responsible for the consequences.

## Credits

**Developed by The Mad Tech Head and his faithful assistant Igor.**

The Mad Tech Head provides the dangerously creative ideas.

Igor provides the implementation, tests, documentation, objections and occasional expressions of genuine concern.

Together, they have produced something that works considerably better than it has any right to.

## Licence

Released under the MIT License. See [LICENSE](LICENSE).

---

**SQLWeb — The Web Server Nobody Asked For™**

*Just because you shouldn't doesn't mean we won't.*

**Igor:** "Master, I would like to formally record my objection."

**Mad Tech Head:** "Objection noted. Implement version 0.2."
