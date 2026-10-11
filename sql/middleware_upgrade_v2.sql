-- SQLWeb middleware schema v2 migration candidate.
-- Execute once against a recognised v1 database.
-- Explicit transaction ensures atomic replacement.

BEGIN IMMEDIATE;

-- The original schema has nine columns.
-- An upgraded schema has ten.
-- This INSERT deliberately requires the original layout.
-- On v2, SQLite raises a column-count error before any
-- destructive table replacement occurs.
CREATE TEMP TABLE sqlweb_legacy_guard (
    rule_id,
    priority,
    enabled,
    method,
    path,
    action,
    status,
    content_type,
    body
);

INSERT INTO sqlweb_legacy_guard
SELECT * FROM middleware_rules;

DROP TABLE sqlweb_legacy_guard;

CREATE TABLE middleware_rules_v2 (
    rule_id INTEGER PRIMARY KEY,
    priority INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1
        CHECK (enabled IN (0, 1)),
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    action TEXT NOT NULL
        CHECK (action IN (
            'ALLOW', 'DENY', 'REDIRECT', 'REWRITE'
        )),
    status INTEGER NOT NULL
        CHECK (status BETWEEN 200 AND 599),
    content_type TEXT NOT NULL,
    body TEXT NOT NULL,
    destination TEXT,

    CHECK (
        (
            action IN ('ALLOW', 'DENY')
            AND destination IS NULL
        )
        OR
        (
            action IN ('REDIRECT', 'REWRITE')
            AND destination IS NOT NULL
            AND typeof(destination) = 'text'
            AND length(destination) BETWEEN 1 AND 512
            AND substr(destination, 1, 1) = '/'
            AND (
                length(destination) = 1
                OR substr(destination, 2, 1) != '/'
            )
            AND destination NOT GLOB '*[^A-Za-z0-9/_~.-]*'
        )
    ),

    CHECK (
        action != 'REDIRECT'
        OR status IN (301, 302, 307, 308)
    ),

    CHECK (
        action != 'REWRITE'
        OR status = 200
    )
);

INSERT INTO middleware_rules_v2 (
    rule_id, priority, enabled, method, path,
    action, status, content_type, body
)
SELECT
    rule_id, priority, enabled, method, path,
    action, status, content_type, body
FROM middleware_rules;

DROP TABLE middleware_rules;

ALTER TABLE middleware_rules_v2
RENAME TO middleware_rules;

CREATE INDEX middleware_rules_lookup
ON middleware_rules (
    enabled, method, path, priority, rule_id
);

COMMIT;
