CREATE TABLE IF NOT EXISTS kits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    grade TEXT NOT NULL,
    series TEXT,
    kit_number INTEGER,
    status TEXT NOT NULL DEFAULT 'Not Started',
    difficulty INTEGER,
    build_quality INTEGER,
    finished_on TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS paints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    brand TEXT,
    code TEXT,
    color TEXT NOT NULL DEFAULT '#808080',
    quantity INTEGER NOT NULL DEFAULT 1,
    running_low INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    runs_out INTEGER NOT NULL DEFAULT 0,
    running_low INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);


CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password_hash TEXT NOT NULL,
    recovery_hash TEXT NOT NULL
);