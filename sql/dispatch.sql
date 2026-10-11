-- SQLWeb: SQL-powered HTTP response dispatch
--
-- Routing is relational.
-- The architectural justification remains theoretical.

WITH matched_route AS (
    SELECT
        status,
        content_type,
        body
    FROM routes
    WHERE method = :method
      AND path = :path
    LIMIT 1
)
SELECT
    status,
    content_type,
    body
FROM matched_route

UNION ALL

SELECT
    404,
    'text/plain; charset=utf-8',
    '404: The requested row does not exist.'

WHERE NOT EXISTS (
    SELECT 1 FROM matched_route
)

LIMIT 1;
