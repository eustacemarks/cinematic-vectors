CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE movies (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title            TEXT NOT NULL,
    release_year     INTEGER,
    major_genre      TEXT,
    mpaa_rating      TEXT,
    director         TEXT,
    distributor      TEXT,
    imdb_rating      NUMERIC(3,1),
    rt_rating        INTEGER,
    production_budget BIGINT,
    running_time_min INTEGER,
    budget_tier      TEXT,
    decade           INTEGER,
    augmented_text   TEXT,
    embedding        vector(768),
    pipeline_version TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_title_year UNIQUE (title, release_year)
);
