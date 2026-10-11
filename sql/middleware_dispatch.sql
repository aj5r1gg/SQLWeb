-- SQLWeb middleware decision query.
--
-- Rules are selected in ascending priority and rule_id order.
-- No matching rule means ALLOW.

WITH selected_rule AS (
    SELECT
        action,
        status,
        content_type,
        body
    FROM middleware_rules
    WHERE enabled = 1
      AND method = :method
      AND path = :path
    ORDER BY priority ASC, rule_id ASC
    LIMIT 1
)

SELECT
    action,
    status,
    content_type,
    body
FROM selected_rule

UNION ALL

SELECT
    'ALLOW',
    200,
    'text/plain; charset=utf-8',
    ''
WHERE NOT EXISTS (
    SELECT 1 FROM selected_rule
)

LIMIT 1;
