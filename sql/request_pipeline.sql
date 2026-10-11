-- SQLWeb SQL-First Request Pipeline
--
-- The Mad Tech Head: "The database IS the application."
-- Igor: "Master, I am removing Python's decision-making privileges."
--
-- Input:
--   :method
--   :path
--
-- Output:
--   action
--   status
--   content_type
--   body
--   location
--   effective_path
--
-- ALLOW and DENY are implemented in this initial version.
-- REDIRECT and REWRITE are deliberately deferred.

WITH
request_input AS (
    SELECT
        :method AS method,
        :path AS path
),

selected_middleware AS MATERIALIZED (
    SELECT
        m.action,
        m.status,
        m.content_type,
        m.body
    FROM middleware_rules AS m
    JOIN request_input AS r
      ON m.method = r.method
     AND m.path = r.path
    WHERE m.enabled = 1
    ORDER BY m.priority ASC, m.rule_id ASC
    LIMIT 1
),

decision AS (
    SELECT
        COALESCE(
            (SELECT action FROM selected_middleware),
            'ALLOW'
        ) AS action
),

selected_route AS MATERIALIZED (
    SELECT
        r.status,
        r.content_type,
        r.body
    FROM routes AS r
    JOIN request_input AS i
      ON r.method = i.method
     AND r.path = i.path
    LIMIT 1
)

SELECT
    CASE
        WHEN :method <> 'GET' THEN 'DENY'
        ELSE d.action
    END AS action,

    CASE
        WHEN :method <> 'GET' THEN 405
        WHEN d.action = 'DENY'
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
        ELSE COALESCE(
            (SELECT content_type FROM selected_route),
            'text/plain; charset=utf-8'
        )
    END AS content_type,

    CASE
        WHEN :method <> 'GET' THEN ''
        WHEN d.action = 'DENY'
        THEN (SELECT body FROM selected_middleware)
        ELSE COALESCE(
            (SELECT body FROM selected_route),
            '404: The requested row does not exist.'
        )
    END AS body,

    NULL AS location,

    (SELECT path FROM request_input) AS effective_path

FROM decision AS d;
