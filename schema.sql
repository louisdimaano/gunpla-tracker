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