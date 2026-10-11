-- SQLWeb: SQL-defined middleware
--
-- The Mad Tech Head:
-- "Let the database decide who gets through."
--
-- Igor:
-- "Master, databases were not designed to be doormen."

CREATE TABLE IF NOT EXISTS middleware_rules (
    rule_id INTEGER PRIMARY KEY,
    priority INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1
        CHECK (enabled IN (0, 1)),
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    action TEXT NOT NULL
        CHECK (action IN ('ALLOW', 'DENY')),
    status INTEGER NOT NULL
        CHECK (status BETWEEN 200 AND 599),
    content_type TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS middleware_rules_lookup
ON middleware_rules (
    enabled,
    method,
    path,
    priority,
    rule_id
);

INSERT OR IGNORE INTO middleware_rules
    (
        rule_id,
        priority,
        enabled,
        method,
        path,
        action,
        status,
        content_type,
        body
    )
VALUES
    (
        1,
        10,
        1,
        'GET',
        '/forbidden',
        'DENY',
        403,
        'text/plain; charset=utf-8',
        '403: Igor refuses entry.'
    ),
    (
        2,
        20,
        1,
        'GET',
        '/igor',
        'ALLOW',
        200,
        'text/plain; charset=utf-8',
        'Igor permits this request.'
    );
