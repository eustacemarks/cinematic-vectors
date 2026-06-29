namespace MovieSearch.Domain;

public record MovieResult(
    string Id,
    string Title,
    int? ReleaseYear,
    string? MajorGenre,
    string? MpaaRating,
    string? Director,
    string? Distributor,
    double? ImdbRating,
    int? RtRating,
    long? ProductionBudget,
    int? RunningTimeMin,
    string? BudgetTier,
    int? Decade,
    double? Similarity
);

public record DatasetStats(
    int TotalMovies,
    List<string> Genres,
    double AvgImdbRating,
    double AvgRtRating,
    int? EarliestYear,
    int? LatestYear
);

public record MovieSearchQuery(
    string Query,
    int TopK = 10,
    string? Genre = null,
    double? MinImdbRating = null,
    string? MpaaRating = null,
    int? Decade = null
);

public interface IMovieSearchService
{
    Task<List<MovieResult>> SearchAsync(MovieSearchQuery query, CancellationToken ct = default);
    Task<MovieResult?> GetByIdAsync(string id, CancellationToken ct = default);
    Task<List<MovieResult>> GetSimilarAsync(string id, int topK = 5, CancellationToken ct = default);
    Task<List<string>> ListGenresAsync(CancellationToken ct = default);
    Task<DatasetStats> GetStatsAsync(CancellationToken ct = default);
}
