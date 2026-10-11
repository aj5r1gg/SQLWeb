# SQLWeb

**The Web Server Nobody Asked For™**

*Because writing a web server in Assembly was far too sensible.*

SQLWeb is an experimental, SQL-first HTTP server in which SQLite makes application decisions and a small Python standard-library adapter handles HTTP transport.

It really works.

Whether it should exist is a separate question.

**Current status:** v0.1.0 is the public release. The `develop` branch contains substantial additional functionality under qualification.

> **Experimental software. Not production-ready. Do not expose it directly to the public internet.**

## The Engineering Team

**The Mad Tech Head** — Chief Architect, Supreme Instigator of Questionable Engineering Decisions, and the man who looked at SQL and thought, "That could be a web server."

**Igor** — Faithful Assistant, Reluctant Voice of Reason, Keeper of the Unit Tests, and Accomplice in Crimes Against Software Architecture.

**Mad Tech Head:** "Igor! Can we build a web server using SQL?"

**Igor:** "Master, that is a spectacularly stupid idea."

**Mad Tech Head:** "Excellent! Start the repository."

**Igor:** "Very good, Master. Shall I prepare the unit tests?"

**Mad Tech Head:** "Obviously. We're not animals."

## What SQLWeb Actually Does

SQLWeb uses SQLite as the application decision engine.

SQLite determines which configured route matches a request, which middleware rule takes precedence, whether a request is permitted, and which response data should be returned.

Python handles TCP connections, HTTP parsing, SQLite connectivity, response validation, HTTP framing and network I/O.

The project does not pretend that SQL opens network sockets or implements the TCP/IP stack.

### Working default-pipeline features on develop

- Local HTTP server using Python's standard library.
- SQLite-backed route definitions and persistent storage.
- SQL-selected HTTP status, content type and response body.
- Dynamic route changes without restarting the server.
- Parameterised SQL request processing.
- SQL-defined ALLOW and DENY middleware.
- Deterministic middleware precedence by priority and rule ID.
- SQL-defined HTTP 405 decisions for unsupported methods.
- SQL-selected Allow response headers.
- SQL-generated 404 fallback responses.
- Response validation and fail-closed HTTP 500 handling.
- Protection against malformed SQL-controlled headers.
- Automated routing, middleware, transport and security tests.
- GitHub Actions test workflow.
- No third-party Python runtime dependencies.

### Qualified development candidates

The `develop` branch additionally contains SQL-defined REDIRECT and REWRITE implementations.

**REDIRECT** supports candidate response codes 301, 302, 307 and 308. SQLite selects the status and destination, while Python validates and transmits the Location header.

**REWRITE** changes the internal route lookup path. The browser URL remains unchanged, middleware is evaluated only once, and rewrite chains are not followed.

Missing rewritten routes return HTTP 404.

The candidate implementation has passed SQL-level and real HTTP integration tests, but it is not yet the default production request pipeline.

A middleware v2 schema migration candidate and an explicit upgrade utility are also under development. The upgrade utility has not completed its qualification programme and must not be applied to an existing database without the qualified upgrade procedure and a verified backup.

## Requirements

- Python 3.10 or newer with standard-library SQLite support.
- A supported operating system with local TCP networking.
- Git to clone the repository.
- An optional SQLite command-line client for manual database inspection.

No pip installation is required for the HTTP server or regression tests.

A questionable sense of humour is recommended.

## Quick Start

Clone the public repository:

    git clone https://github.com/aj5r1gg/SQLWeb.git
    cd SQLWeb

Start the server:

    python3 server.py

By default, SQLWeb listens on 127.0.0.1, port 8080.

In another terminal, try:

    curl -i http://127.0.0.1:8080/
    curl -i http://127.0.0.1:8080/health
    curl -i http://127.0.0.1:8080/igor
    curl -i http://127.0.0.1:8080/forbidden
    curl -i http://127.0.0.1:8080/missing

Stop the server with Ctrl+C.

### Running the development branch

To inspect the more advanced SQL middleware implementation:

    git switch develop

If you cloned the repository before the development branch existed, fetch it first:

    git fetch origin
    git switch --track origin/develop

The normal development server still uses the committed default SQL pipeline, not the experimental REDIRECT/REWRITE candidate.

### Default endpoints

| Method | Path | Response |
|---|---|---|
| GET | `/` | 200, SQLWeb introduction |
| GET | `/health` | 200, JSON health response |
| GET | `/igor` | 200, Igor acknowledges the Master |
| GET | `/forbidden` | 403, SQL middleware denial on develop |
| GET | Unknown path | 404, SQL-selected fallback |
| POST | Any path | 405, with Allow: GET |
| HEAD | Any path | 405, with Allow: GET and no body |

The initial public v0.1.0 release predates the SQL middleware implementation. The `/forbidden` endpoint and newer response-policy behaviour described here belong to `develop`.

## Architecture

The current development request flow is:

1. Python receives and parses an HTTP request.
2. Python binds the HTTP method and URL path as SQL parameters.
3. SQLite selects the highest-precedence matching middleware rule.
4. SQLite determines the response policy and route selection.
5. SQLite returns a seven-column response record.
6. Python validates the response and emits HTTP headers and body.

The seven response fields are:

| Field | Purpose |
|---|---|
| `action` | SQL-selected middleware decision |
| `status` | HTTP response status |
| `content_type` | Response media type |
| `body` | Response body text |
| `location` | Optional redirect destination |
| `effective_path` | SQL-selected internal route path |
| `allow_methods` | Optional HTTP Allow header |

Python validates response values before transmitting them. It is not responsible for interpreting middleware priority or performing internal route rewrites.

### Important implementation files

| File | Responsibility |
|---|---|
| `server.py` | HTTP transport and response safety |
| `sql/schema.sql` | Route schema and default routes |
| `sql/middleware_schema.sql` | Default ALLOW/DENY middleware schema |
| `sql/request_pipeline.sql` | Active SQL decision pipeline on develop |
| `sql/request_pipeline_v2_candidate.sql` | Experimental REDIRECT/REWRITE pipeline |
| `sql/middleware_migrate_v2_candidate.sql` | Experimental middleware schema upgrade |
| `tests/` | Permanent HTTP and security regression tests |

The older `sql/dispatch.sql` and `sql/middleware_dispatch.sql` files remain in the repository, but the development server uses the consolidated request pipeline.

### Middleware precedence

Enabled rules are evaluated by ascending numerical priority and then ascending rule ID.

Only the first matching rule decides the middleware action.

No matching rule means ALLOW.

An explicit ALLOW continues to normal route lookup; it does not invent a missing route.

An explicit DENY returns the middleware-selected response.

## Adding a Route

Start the server once so it creates `sqlweb.db`.

Open the database using the optional SQLite command-line client:

    sqlite3 sqlweb.db

Execute:

    INSERT INTO routes
        (method, path, status, content_type, body)
    VALUES
        ('GET', '/hello', 200,
         'text/plain; charset=utf-8',
         'Hello from SQLWeb!');

Exit SQLite:

    .quit

Request the new endpoint:

    curl -i http://127.0.0.1:8080/hello

SQLWeb reads committed route data during subsequent requests. A restart is not required.

For the development middleware engine, rules may likewise be changed in the database subject to its schema constraints and priority ordering.

## Testing and Qualification

Run the full local regression suite:

    python3 -m unittest discover -s tests -v

At development checkpoint M3-L.1, the complete suite passed **42 out of 42 tests**.

The permanent suite covers:

- Default routes and dynamic route insertion.
- SQL middleware ALLOW and DENY behaviour.
- Priority and rule-ID tie-breaking.
- Parameter binding and injection resistance.
- Unsupported HTTP methods.
- Missing database objects and HTTP 500 fallback.
- Invalid SQL response statuses and headers.
- SQL-controlled Location header safety.
- Four candidate redirect status codes.
- Internal rewrite behaviour, missing routes and loop prevention.
- Real HTTP responses using temporary SQLite databases.

Some tests deliberately generate HTTP 500 responses to establish fail-closed behaviour.

The REDIRECT/REWRITE regression tests currently load the candidate SQL pipeline rather than the default installed pipeline. Passing them does not imply those transforms are enabled in normal server execution.

Local tests and remote GitHub Actions are distinct qualifications. Do not assume CI has passed without checking its results.

## Security and Limitations

SQLWeb is an experimental engineering project, not a hardened internet-facing web server.

The default listener binds to localhost.

The current project does not provide production-grade:

- TLS termination.
- Authentication and access-control management.
- Rate limiting and abuse prevention.
- Comprehensive request-size and resource limits.
- HTTP/2 or HTTP/3.
- Exhaustive HTTP protocol conformance.
- Security-reviewed deployment and operational hardening.

Middleware ALLOW/DENY rules are not a substitute for a complete authentication and authorisation system.

The response adapter checks SQL-selected headers and values, but this does not establish comprehensive security.

**Do not deploy SQLWeb directly onto a publicly accessible interface.**

## Development Status and Roadmap

| Capability | Status |
|---|---|
| Local HTTP server | Implemented |
| SQLite route dispatch | Implemented |
| SQL-generated response decisions | Implemented |
| Dynamic routes | Implemented |
| SQL ALLOW/DENY middleware | Implemented on develop |
| Deterministic middleware priority | Implemented on develop |
| SQL-defined method policy and Allow header | Implemented on develop |
| Unified SQL request pipeline | Implemented on develop |
| Redirect/rewrite SQL pipeline | Candidate qualified |
| Redirect/rewrite HTTP integration | Candidate qualified |
| Middleware v2 schema migration | Candidate qualified in selected scenarios |
| Explicit migration upgrade utility | Further qualification required |
| Default-pipeline transform integration | Pending |
| Database migration deployment procedure | Pending |
| SQL-defined request logging | Planned |
| SQL-based performance profiling | Planned |
| Comparative server benchmarking | Planned |
| SQL-based template rendering | Exploratory |

No comparative performance claim against Nginx, Apache, Caddy or another server is made.

### Branches

- `main` — public v0.1.0 baseline.
- `develop` — ongoing engineering and qualification.

The development branch must not be treated as a production release.

## Frequently Asked Questions

**Is this a good idea?**

No.

**Does it actually work?**

Yes.

**Is it a pure-SQL web server?**

No. SQLite provides the application decision engine; Python provides HTTP transport.

**Why SQL?**

Because Assembly was already taken.

**Is it production-ready?**

Absolutely not.

**Is it a joke?**

The architectural decision is a joke. The implementation and tests are real.

**Will it outperform Nginx?**

No such claim has been made or demonstrated.

**Can I contribute?**

Yes. Bug reports should include reproduction steps, and pull requests should include relevant tests.

**Who is responsible?**

The Mad Tech Head. Igor wishes to clarify that he was following instructions.

## Development Philosophy

1. The implementation must actually work.
2. Tests must verify meaningful behaviour.
3. No invented benchmarks, results or capabilities.
4. SQL should own application decisions wherever practical.
5. Python must retain necessary transport safety.
6. Database migrations must preserve existing data.
7. Failures should be deterministic and recoverable.
8. Deliberately absurd architecture is encouraged.
9. Deliberately broken software is not.
10. Igor is permitted to object.

The Mad Tech Head is permitted to ignore Igor.

Both remain responsible for the consequences.

**Rejected feature:** An ORM to avoid writing SQL. Igor considers this philosophically indefensible.

## Credits

**Developed by The Mad Tech Head and his faithful assistant Igor.**

The Mad Tech Head supplies the dangerously creative ideas.

Igor supplies implementation assistance, tests, documentation, objections and occasional expressions of genuine concern.

Together, they have produced something that works considerably better than it has any right to.

## Licence

Released under the MIT License. See [LICENSE](LICENSE).

---

**SQLWeb — The Web Server Nobody Asked For™**

*Just because you shouldn't doesn't mean we won't.*

**Igor:** "Master, I would like to formally record my objection."

**Mad Tech Head:** "Objection noted. Implement version 0.2."
