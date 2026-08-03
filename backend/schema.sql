-- The product identity: roaster + name. Always known at submit time (typed
-- or autocompleted) — resolved synchronously, never waits on AI.
CREATE TABLE bean_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roaster TEXT NOT NULL,
    bean_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One row per coffee "instance" — a bag you bought, OR a single cup you had
-- somewhere. Saved immediately on submit; detail fields fill in later by
-- background extraction once photo upload is built in 0.2.0 (or typed
-- manually before that).
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bean_profile_id INTEGER NOT NULL REFERENCES bean_profiles(id),
    user_id INTEGER REFERENCES users(id),   -- unused until 1.8.0 multi-user
    entry_type TEXT NOT NULL,       -- 'bag' or 'cafe_cup'
    cafe_name TEXT,                  -- only relevant for entry_type = 'cafe_cup'
    entry_date DATE,
    date_entered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    price_paid REAL,
    currency TEXT DEFAULT 'CAD',

    extraction_status TEXT DEFAULT 'not_applicable',  -- 'pending' (photos submitted, awaiting background job) / 'complete' / 'failed' / 'not_applicable' (no photos, fully manual)
    extraction_source TEXT,          -- 'claude' or 'manual'

    origin_country TEXT,
    region TEXT,
    farm_producer TEXT,
    altitude_m INTEGER,
    variety TEXT,                    -- e.g. Bourbon, Typica, Geisha
    process TEXT,                     -- washed, natural, honey, anaerobic, etc.
    co_ferment_status TEXT DEFAULT 'unknown',   -- 'yes' / 'no' / 'unknown'
    co_ferment_ingredient TEXT,       -- e.g. 'lychee', 'cascara', 'wine yeast' — populated when co_ferment_status = 'yes' and the label names it
    certifications TEXT,              -- organic, fair trade, direct trade, etc.
    roast_level TEXT,                 -- light, medium, medium-dark, dark
    printed_tasting_notes TEXT,       -- flavor notes from the bag/menu/info card
    roast_date DATE,
    bag_weight_g INTEGER,

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Any number of photos per entry. Table exists from 0.1.0, first used in
-- 0.2.0 once photo upload is built.
CREATE TABLE entry_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    photo_path TEXT NOT NULL,
    upload_order INTEGER,
    date_entered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- One row per rating EVENT. An entry can have several (revisit a bag,
-- reorder the same cafe drink).
CREATE TABLE ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id),
    user_id INTEGER REFERENCES users(id),   -- unused until 1.8.0 multi-user

    score REAL NOT NULL,             -- 0-10, required
    narrative_notes TEXT,            -- optional free text

    -- Advanced / optional, collapsed by default in the UI:
    acidity_score REAL,
    body_score REAL,
    sweetness_score REAL,
    brew_style TEXT,                  -- 'Pour Over' (default), 'Espresso', 'French Press', 'Cafe-made', 'Other'
    repurchase TEXT,                  -- yes / no / maybe

    date_entered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP    -- unused until 1.1.0 edit support
);

-- Unused until 1.8.0 multi-user/auth.
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Unused until 1.7.0 Settings UI.
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Unused until 1.3.0 data backup sinks. Tracks last successful export per sink.
CREATE TABLE export_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sink TEXT NOT NULL,              -- 'local_xlsx' or 'github'
    exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT                       -- 'success' or 'failed'
);

-- Unused until 1.4.0 AI narrative insights. Caches generated summaries.
CREATE TABLE insight_narratives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    window_type TEXT,                -- 'all_time' or 'recent'
    summary_text TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
