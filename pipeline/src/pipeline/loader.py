import logging
import asyncpg
import pandas as pd

logger = logging.getLogger(__name__)

INSERT_SQL = """
INSERT INTO movies (
    title, release_year, major_genre, mpaa_rating, director,
    distributor, imdb_rating, rt_rating, production_budget,
    running_time_min, budget_tier, decade, augmented_text,
    embedding, pipeline_version
)
VALUES (
    $1, $2, $3, $4, $5,
    $6, $7, $8, $9,
    $10, $11, $12, $13,
    $14, $15
)
ON CONFLICT (title, release_year) DO NOTHING
"""


async def load(
    df: pd.DataFrame,
    dsn: str,
    pipeline_version: str = "1.0.0",
) -> int:
    """
    Upsert records into pgvector.
    Returns count of rows inserted.
    """
    conn = await asyncpg.connect(dsn)
    inserted = 0

    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

        for _, row in df.iterrows():
            title = row.get("Title")
            if not isinstance(title, str) or not title.strip():
                continue  # skip rows with no title

            await conn.execute(
                INSERT_SQL,
                str(row["Title"]),
                int(row["Release Year"]) if pd.notna(row.get("Release Year")) else None,
                str(row["Major Genre"]) if pd.notna(row.get("Major Genre")) else None,
                str(row["MPAA Rating"]) if pd.notna(row.get("MPAA Rating")) else None,
                str(row["Director"]) if pd.notna(row.get("Director")) else None,
                str(row["Distributor"]) if pd.notna(row.get("Distributor")) else None,
                float(row["IMDB Rating"]) if pd.notna(row.get("IMDB Rating")) else None,
                int(row["Rotten Tomatoes Rating"]) if pd.notna(row.get("Rotten Tomatoes Rating")) else None,
                int(row["Production Budget"]) if pd.notna(row.get("Production Budget")) else None,
                int(row["Running Time min"]) if pd.notna(row.get("Running Time min")) else None,
                str(row["budget_tier"]) if pd.notna(row.get("budget_tier")) else None,
                int(row["decade"]) if pd.notna(row.get("decade")) else None,
                str(row["augmented_text"]) if pd.notna(row.get("augmented_text")) else None,
                str(row["embedding"]),
                pipeline_version,
            )
            inserted += 1
    finally:
        await conn.close()

    logger.info("Loaded %d records into pgvector", inserted)
    return inserted
