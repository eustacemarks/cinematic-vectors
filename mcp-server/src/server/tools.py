import httpx
import asyncpg
from fastmcp import FastMCP
from server.models import MovieResult, DatasetStats
from config import EMBEDDING_URL, dsn

mcp = FastMCP("movie-search")


async def _embed(text: str) -> list[float]:
    """Get embedding vector for a query string."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{EMBEDDING_URL}/embed", json={"input": text})
        r.raise_for_status()
        return r.json()["embedding"]


def _row_to_movie(row: dict, similarity: float | None = None) -> MovieResult:
    return MovieResult(
        id=str(row["id"]),
        title=row["title"],
        release_year=row["release_year"],
        major_genre=row["major_genre"],
        mpaa_rating=row["mpaa_rating"],
        director=row["director"],
        distributor=row["distributor"],
        imdb_rating=float(row["imdb_rating"]) if row["imdb_rating"] else None,
        rt_rating=row["rt_rating"],
        production_budget=row["production_budget"],
        running_time_min=row["running_time_min"],
        budget_tier=row["budget_tier"],
        decade=row["decade"],
        similarity=similarity,
    )


@mcp.tool()
async def search_movies_by_description(
    query: str,
    top_k: int = 10,
    genre_filter: str | None = None,
    min_imdb_rating: float | None = None,
    mpaa_rating: str | None = None,
    decade: int | None = None,
) -> list[MovieResult]:
    """
    Search movies using natural language description.
    Performs semantic vector similarity search with optional metadata filters.
    Returns ranked results with similarity scores.
    """
    embedding = await _embed(query)

    conditions = ["TRUE"]
    params: list = [str(embedding)]

    if genre_filter:
        params.append(genre_filter)
        conditions.append(f"major_genre ILIKE ${len(params)}")
    if min_imdb_rating is not None:
        params.append(min_imdb_rating)
        conditions.append(f"imdb_rating >= ${len(params)}")
    if mpaa_rating:
        params.append(mpaa_rating)
        conditions.append(f"mpaa_rating ILIKE ${len(params)}")
    if decade:
        params.append(decade)
        conditions.append(f"decade = ${len(params)}")

    params.append(top_k)
    where = " AND ".join(conditions)

    sql = f"""
        SELECT *, 1 - (embedding <=> $1::vector) AS similarity
        FROM movies
        WHERE {where}
        ORDER BY embedding <=> $1::vector
        LIMIT ${len(params)}
    """

    conn = await asyncpg.connect(dsn())
    try:
        rows = await conn.fetch(sql, *params)
    finally:
        await conn.close()

    return [_row_to_movie(dict(r), r["similarity"]) for r in rows]


@mcp.tool()
async def get_movie_by_title(title: str) -> MovieResult | None:
    """Retrieve a specific movie by exact or fuzzy title match."""
    conn = await asyncpg.connect(dsn())
    try:
        row = await conn.fetchrow(
            "SELECT * FROM movies WHERE title ILIKE $1 LIMIT 1",
            f"%{title}%",
        )
    finally:
        await conn.close()
    return _row_to_movie(dict(row)) if row else None


@mcp.tool()
async def get_similar_movies(movie_id: str, top_k: int = 5) -> list[MovieResult]:
    """Given a movie ID, return the most semantically similar movies."""
    conn = await asyncpg.connect(dsn())
    try:
        source = await conn.fetchrow(
            "SELECT embedding FROM movies WHERE id = $1", movie_id
        )
        if not source:
            return []
        rows = await conn.fetch(
            """
            SELECT *, 1 - (embedding <=> $1::vector) AS similarity
            FROM movies
            WHERE id != $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            source["embedding"],
            movie_id,
            top_k,
        )
    finally:
        await conn.close()
    return [_row_to_movie(dict(r), r["similarity"]) for r in rows]


@mcp.tool()
async def list_genres() -> list[str]:
    """Return all distinct genres available in the dataset."""
    conn = await asyncpg.connect(dsn())
    try:
        rows = await conn.fetch(
            "SELECT DISTINCT major_genre FROM movies "
            "WHERE major_genre IS NOT NULL ORDER BY major_genre"
        )
    finally:
        await conn.close()
    return [r["major_genre"] for r in rows]


@mcp.tool()
async def get_dataset_stats() -> DatasetStats:
    """Return summary statistics about the movie dataset."""
    conn = await asyncpg.connect(dsn())
    try:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*)                        AS total_movies,
                AVG(imdb_rating)                AS avg_imdb_rating,
                AVG(rt_rating)                  AS avg_rt_rating,
                MIN(release_year)               AS earliest_year,
                MAX(release_year)               AS latest_year
            FROM movies
            """
        )
        genre_rows = await conn.fetch(
            "SELECT DISTINCT major_genre FROM movies "
            "WHERE major_genre IS NOT NULL ORDER BY major_genre"
        )
    finally:
        await conn.close()
    return DatasetStats(
        total_movies=row["total_movies"],
        genres=[r["major_genre"] for r in genre_rows],
        avg_imdb_rating=round(float(row["avg_imdb_rating"] or 0), 2),
        avg_rt_rating=round(float(row["avg_rt_rating"] or 0), 2),
        earliest_year=row["earliest_year"],
        latest_year=row["latest_year"],
    )
