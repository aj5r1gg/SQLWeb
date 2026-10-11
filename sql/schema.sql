-- SQLWeb: The Web Server Nobody Asked For
-- Database schema
--
-- The Mad Tech Head: "HTTP belongs in a database."
-- Igor: "That is not what databases are for, Master."

CREATE TABLE IF NOT EXISTS routes (
    method       TEXT NOT NULL,
    path         TEXT NOT NULL,
    status       INTEGER NOT NULL
                 CHECK (status BETWEEN 200 AND 599),
    content_type TEXT NOT NULL,
    body         TEXT NOT NULL,

    PRIMARY KEY (method, path)
);

INSERT OR IGNORE INTO routes
    (method, path, status, content_type, body)
VALUES
    (
        'GET',
        '/',
        200,
        'text/plain; charset=utf-8',
        'SQLWeb — The Web Server Nobody Asked For'
    ),
    (
        'GET',
        '/health',
        200,
        'application/json',
        '{"status":"ok","engine":"SQLWeb","database":"SQLite"}'
    ),
    (
        'GET',
        '/igor',
        200,
        'text/plain; charset=utf-8',
        'Yes, Master. Unfortunately, it works.'
    );
