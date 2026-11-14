-- SQLite 表结构草稿。负责人：C（后端）。
-- 可以按自己的实现调整表结构，但 Repository 的方法签名和行为约定不能改。
-- 嵌套字段（tags / open_periods / options）存 JSON 文本，读回时还原成 tuple / 枚举。

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS campuses (
    id       TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    aliases  TEXT NOT NULL DEFAULT '[]'      -- JSON array
);

CREATE TABLE IF NOT EXISTS venues (
    id            TEXT PRIMARY KEY,
    campus_id     TEXT NOT NULL REFERENCES campuses(id),
    name          TEXT NOT NULL,
    kind          TEXT NOT NULL,
    location      TEXT NOT NULL DEFAULT '',
    open_periods  TEXT NOT NULL DEFAULT '[]',-- JSON array
    tags          TEXT NOT NULL DEFAULT '[]',-- JSON array
    available     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS dishes (
    id          TEXT PRIMARY KEY,
    venue_id    TEXT NOT NULL REFERENCES venues(id),
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price_fen   INTEGER NOT NULL CHECK (price_fen >= 0),
    tags        TEXT NOT NULL DEFAULT '[]',  -- JSON array
    description TEXT NOT NULL DEFAULT '',
    available   INTEGER NOT NULL DEFAULT 1,
    source      TEXT NOT NULL DEFAULT 'DEMO',
    updated_at  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_dishes_venue ON dishes(venue_id);

CREATE TABLE IF NOT EXISTS reviews (
    review_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    dish_id     TEXT NOT NULL REFERENCES dishes(id),
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment     TEXT NOT NULL DEFAULT '',
    author      TEXT NOT NULL,
    created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reviews_dish_time ON reviews(dish_id, created_at DESC);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    dish_id     TEXT NOT NULL,
    venue_id    TEXT NOT NULL,
    mode        TEXT NOT NULL,
    created_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decisions_time ON decisions(created_at DESC);

CREATE TABLE IF NOT EXISTS vote_rooms (
    code        TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    options     TEXT NOT NULL,               -- JSON array of {option_id, label}
    creator     TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    closes_at   INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'OPEN'
);

CREATE TABLE IF NOT EXISTS vote_ballots (
    room_code    TEXT NOT NULL REFERENCES vote_rooms(code) ON DELETE CASCADE,
    voter_token  TEXT NOT NULL,
    option_id    TEXT NOT NULL,
    created_at   INTEGER NOT NULL,
    PRIMARY KEY (room_code, voter_token)
);
