import asyncio
import logging
import os
import json

from alembic.config import Config
from alembic import command
from vega_datasets import data as vega_data

from pipeline.cleaning import clean
from pipeline.imputation import impute
from pipeline.augmentation import augment
from pipeline.embedding import generate_embeddings
from pipeline.loader import load

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_dsn() -> str:
    return (
        f"postgresql://{os.environ['POSTGRES_USER']}"
        f":{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ.get('POSTGRES_HOST', 'localhost')}"
        f":5432/{os.environ['POSTGRES_DB']}"
    )


def run_migrations(dsn: str) -> None:
    logger.info("── Running schema bootstrap ─────────────────")
    import psycopg2
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    cur.execute("""
        CREATE TABLE IF NOT EXISTS movies (
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
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_embedding ON movies USING hnsw (embedding vector_cosine_ops)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_genre ON movies (major_genre)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_decade ON movies (decade)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_mpaa ON movies (mpaa_rating)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_imdb ON movies (imdb_rating)")
    cur.close()
    conn.close()
    logger.info("Schema bootstrap complete")


async def run() -> None:
    embedding_url = os.environ["EMBEDDING_URL"]
    pipeline_version = os.environ.get("PIPELINE_VERSION", "1.0.0")
    batch_size = int(os.environ.get("BATCH_SIZE", "64"))
    dsn = build_dsn()

    run_migrations(dsn)

    logger.info("── Loading dataset ──────────────────────────")
    df = vega_data.movies()
    logger.info("Loaded %d raw records", len(df))

    logger.info("── Cleaning ─────────────────────────────────")
    df, clean_report = clean(df)

    logger.info("── Imputing ─────────────────────────────────")
    df, impute_report = impute(df)

    logger.info("── Augmenting ───────────────────────────────")
    df = augment(df)

    logger.info("── Generating embeddings ────────────────────")
    df = await generate_embeddings(df, embedding_url, batch_size)

    logger.info("── Loading into pgvector ────────────────────")
    inserted = await load(df, dsn, pipeline_version)

    summary = {
        "records_inserted": inserted,
        "cleaning": clean_report,
        "imputation": impute_report,
    }
    print("\n── Pipeline Summary ─────────────────────────")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(run())
