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

### Implemented features in v0.2.0

- Local HTTP server using Python's standard library.
- SQLite-backed route definitions and persistent storage.
- SQL-selected HTTP status, content type and response body.
- Dynamic route changes without restarting the server.
- Parameterised SQL request processing.
- SQL-defined ALLOW, DENY, REDIRECT and REWRITE middleware.
- Deterministic middleware precedence by priority and rule ID.
- SQL-defined HTTP 405 decisions and Allow headers.
- SQL-generated HTTP 404 fallback responses.
- Redirect responses with status 301, 302, 307 or 308.
- Single-hop internal route rewriting without changing the browser URL.
- Schema-aware selection of legacy v1 or v2 SQL dispatch.
- Fresh databases initialized with middleware v2.
- Explicit offline v1-to-v2 upgrade with verified SQLite backup.
- Backup restoration and upgrade regression tests.
- Response validation and fail-closed HTTP 500 handling.
- Protection against malformed SQL-controlled response headers.
- Automated routing, middleware, transport and security tests.
- GitHub Actions test workflow.
- No third-party Python runtime dependencies.

### Redirect and rewrite semantics

**REDIRECT** causes SQLite to select an HTTP redirect status
and destination. Python validates the Location header before
transmitting it. Supported statuses are 301, 302, 307 and 308.

**REWRITE** changes the internal route lookup path while leaving
the requested browser URL unchanged. Middleware is evaluated
once. Rewrite chains are not followed, and a missing rewritten
route returns HTTP 404.

These operations are available in the normal server when its
database uses the v2 middleware schema.

Existing v1 databases retain legacy ALLOW/DENY behaviour until
explicitly upgraded. No automatic migration occurs at startup.

These features were qualified on `develop` before the v0.2.0 release.

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

### Installing v0.2.0

For the published release, clone the repository and select
the versioned release tag:

    git clone https://github.com/aj5r1gg/SQLWeb.git
    cd SQLWeb
    git fetch --tags
    git switch --detach v0.2.0
    python3 server.py

The v0.2.0 tag must exist on GitHub before these release
instructions can be used.

A fresh database uses middleware v2 automatically.
REDIRECT and REWRITE are available through normal request
dispatch.

To work on ongoing development rather than a release:

    git switch develop

Existing v1 databases are not automatically migrated.
Follow the offline upgrade instructions below.

### Upgrading an existing v1 database

**Stop SQLWeb and all other writers to the database before
upgrading. Concurrent upgrades are not supported.**

From the repository root, run:

    python3 tools/upgrade_middleware.py \
        --database sqlweb.db \
        --backup sqlweb-before-v2.db \
        --apply

The upgrade utility requires explicit `--apply` authorisation
and a new backup filename. It refuses to overwrite an existing
backup file.

The utility uses SQLite's backup API, checks backup integrity,
validates the recognised legacy middleware schema, and
performs the schema replacement transactionally.

The database's existing routes and middleware records are
preserved. Once upgraded, SQLWeb automatically selects the
v2 SQL request pipeline.

**Do not remove the backup after upgrading.** Confirm that
the upgraded application behaves correctly before treating
the upgrade as complete.

If migration fails, inspect the error and database state before
retrying. Do not bypass schema validation.

### Recovering from an upgrade

Keep SQLWeb and all database writers stopped.

The backup contains the pre-upgrade database. Recovery should
be performed to a separate database file first, rather than
overwriting the existing database blindly.

For example, with the optional SQLite CLI:

    sqlite3 sqlweb-before-v2.db ".backup 'sqlweb-restored.db'"

Verify the restored database:

    sqlite3 sqlweb-restored.db "PRAGMA integrity_check;"

Inspect its data and schema before deciding whether to replace
the application database. Preserve the failed database for
diagnosis.

The recovery procedure was exercised against disposable
databases during release-candidate qualification.

SQLWeb does not automatically roll back an upgrade by restoring
its backup.

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

Version 0.1.0 predates the expanded middleware implementation. The response-policy behaviour described here is included in v0.2.0.

## Architecture

The current SQLWeb request flow is:

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
| `server.py` | HTTP transport, initialization, schema selection and response safety |
| `sql/schema.sql` | Route schema and default routes |
| `sql/middleware_schema.sql` | Canonical legacy v1 middleware schema |
| `sql/request_pipeline.sql` | Legacy v1 SQL request pipeline |
| `sql/request_pipeline_v2.sql` | v2 SQL pipeline including REDIRECT and REWRITE |
| `sql/middleware_upgrade_v2.sql` | Transactional v1-to-v2 schema definition and migration |
| `tools/upgrade_middleware.py` | Guarded offline upgrade and verified backup |
| `tests/` | Permanent HTTP, migration and security regression tests |

The server selects the applicable SQL pipeline from the
verified middleware table and index definitions.

Fresh v2 databases are built using the legacy schema followed
by the same qualified v2 migration SQL. Existing databases are
not migrated automatically.

Older dispatch and candidate SQL files are retained in the
repository for development history. They are not selected by
the normal v0.2.0 request handler.

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

Middleware rules can likewise be changed in the database subject to the active schema constraints and deterministic priority ordering.

## Testing and Qualification

Run the complete regression suite:

    python3 -m unittest discover -s tests -v

At checkpoint M3-RC.4, the local suite passed **61 out of 61
tests**. This is a recorded qualification result, not a claim
about future changes or remote CI.

The suite covers:

- Default routes and dynamic route insertion.
- SQL middleware ALLOW and DENY behaviour.
- Deterministic middleware priority and rule-ID tie-breaking.
- Parameter binding and injection resistance.
- HTTP method restrictions and Allow headers.
- Invalid response statuses and unsafe headers.
- Redirect statuses, Location validation and HTTP behaviour.
- Internal rewrites, missing routes and single-hop semantics.
- Legacy and v2 middleware schema identification.
- Real HTTP integration without replacing the installed pipeline.
- Fresh v2 initialization and preservation of existing v1 data.
- Rejection of unsupported middleware schemas.
- Guarded migration, data preservation and transaction rollback.
- Verified SQLite backups, overwrite prevention and restoration.

The offline migration and recovery procedure was additionally
rehearsed using disposable databases and the real upgrade CLI.

Some tests intentionally generate HTTP 500 responses to confirm
fail-closed behaviour.

Local qualification and GitHub Actions qualification are
separate. Remote CI must be checked for the release revision.

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

| Capability | v0.2.0 status |
|---|---|
| Local HTTP server | Implemented |
| SQLite route dispatch | Implemented |
| SQL-generated response decisions | Implemented |
| Dynamic routes | Implemented |
| SQL ALLOW/DENY middleware | Implemented |
| Deterministic middleware priority | Implemented |
| SQL-defined method policy and Allow header | Implemented |
| Unified SQL request pipelines | Implemented |
| Redirect and rewrite SQL pipeline | Integrated |
| Redirect and rewrite HTTP integration | Qualified locally |
| Fresh v2 database initialization | Implemented |
| Existing v1 database compatibility | Implemented |
| Explicit middleware upgrade utility | Qualified offline |
| Verified SQLite backup and recovery | Qualified offline |
| SQL-defined request logging | Planned |
| SQL-based performance profiling | Planned |
| Comparative server benchmarking | Planned |
| SQL-based template rendering | Exploratory |

No comparative performance claim against Nginx, Apache,
Caddy or another web server is made.

### Branches and releases

- `main` — stable release branch.
- `develop` — ongoing development and qualification.
- `v0.2.0` — versioned release tag, once published.

A release is available only after its tag has been pushed
and verified on GitHub.

SQLWeb remains experimental software and is not intended
for direct deployment to an untrusted public network.

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
