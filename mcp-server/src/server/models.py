from pydantic import BaseModel


class MovieResult(BaseModel):
    id: str
    title: str
    release_year: int | None
    major_genre: str | None
    mpaa_rating: str | None
    director: str | None
    distributor: str | None
    imdb_rating: float | None
    rt_rating: int | None
    production_budget: int | None
    running_time_min: int | None
    budget_tier: str | None
    decade: int | None
    similarity: float | None = None


class DatasetStats(BaseModel):
    total_movies: int
    genres: list[str]
    avg_imdb_rating: float
    avg_rt_rating: float
    earliest_year: int | None
    latest_year: int | None
