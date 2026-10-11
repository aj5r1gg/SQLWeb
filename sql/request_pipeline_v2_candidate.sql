-- SQLWeb M3-J: SQL-defined request transformations.
-- Seven-column transport contract:
-- action, status, content_type, body,
-- location, effective_path, allow_methods.

WITH
request_input AS (
    SELECT :method AS method, :path AS path
),

selected_middleware AS MATERIALIZED (
    SELECT
        m.action,
        m.status,
        m.content_type,
        m.body,
        m.destination
    FROM middleware_rules AS m
    JOIN request_input AS i
      ON m.method = i.method
     AND m.path = i.path
    WHERE m.enabled = 1
    ORDER BY m.priority ASC, m.rule_id ASC
    LIMIT 1
),

decision AS (
    SELECT COALESCE(
        (SELECT action FROM selected_middleware),
        'ALLOW'
    ) AS action
),

effective_request AS (
    SELECT
        i.method,
        CASE
            WHEN d.action = 'REWRITE'
            THEN (SELECT destination FROM selected_middleware)
            ELSE i.path
        END AS path
    FROM request_input AS i
    CROSS JOIN decision AS d
),

selected_route AS MATERIALIZED (
    SELECT r.status, r.content_type, r.body
    FROM routes AS r
    JOIN effective_request AS e
      ON r.method = e.method
     AND r.path = e.path
    LIMIT 1
)

SELECT
    CASE
        WHEN :method <> 'GET' THEN 'DENY'
        ELSE d.action
    END AS action,

    CASE
        WHEN :method <> 'GET' THEN 405
        WHEN d.action IN ('DENY', 'REDIRECT')
        THEN (SELECT status FROM selected_middleware)
        ELSE COALESCE(
            (SELECT status FROM selected_route),
            404
        )
    END AS status,

    CASE
        WHEN :method <> 'GET'
        THEN 'text/plain; charset=utf-8'
        WHEN d.action = 'DENY'
        THEN (SELECT content_type FROM selected_middleware)
        WHEN d.action = 'REDIRECT'
        THEN 'text/plain; charset=utf-8'
        ELSE COALESCE(
            (SELECT content_type FROM selected_route),
            'text/plain; charset=utf-8'
        )
    END AS content_type,

    CASE
        WHEN :method <> 'GET' THEN ''
        WHEN d.action = 'DENY'
        THEN (SELECT body FROM selected_middleware)
        WHEN d.action = 'REDIRECT' THEN ''
        ELSE COALESCE(
            (SELECT body FROM selected_route),
            '404: The requested row does not exist.'
        )
    END AS body,

    CASE
        WHEN :method = 'GET'
         AND d.action = 'REDIRECT'
        THEN (SELECT destination FROM selected_middleware)
        ELSE NULL
    END AS location,

    (SELECT path FROM effective_request) AS effective_path,

    CASE
        WHEN :method <> 'GET' THEN 'GET'
        ELSE NULL
    END AS allow_methods

FROM decision AS d;
