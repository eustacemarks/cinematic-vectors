using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using MovieSearch.Domain;

namespace MovieSearch.Infrastructure;

public class McpMovieSearchService(HttpClient http) : IMovieSearchService
{
    private static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };

    private async Task<T> CallTool<T>(string tool, object args, CancellationToken ct)
    {
        var body = JsonSerializer.Serialize(new { tool, arguments = args }, Json);
        var response = await http.PostAsync(
            "/mcp/tool",
            new StringContent(body, Encoding.UTF8, "application/json"),
            ct
        );
        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync(ct);
        return JsonSerializer.Deserialize<T>(json, Json)!;
    }

    public Task<List<MovieResult>> SearchAsync(MovieSearchQuery q, CancellationToken ct = default) =>
        CallTool<List<MovieResult>>("search_movies_by_description", new
        {
            query = q.Query,
            top_k = q.TopK,
            genre_filter = q.Genre,
            min_imdb_rating = q.MinImdbRating,
            mpaa_rating = q.MpaaRating,
            decade = q.Decade,
        }, ct);

    public Task<MovieResult?> GetByIdAsync(string id, CancellationToken ct = default) =>
        CallTool<MovieResult?>("get_movie_by_title", new { title = id }, ct);

    public Task<List<MovieResult>> GetSimilarAsync(string id, int topK = 5, CancellationToken ct = default) =>
        CallTool<List<MovieResult>>("get_similar_movies", new { movie_id = id, top_k = topK }, ct);

    public Task<List<string>> ListGenresAsync(CancellationToken ct = default) =>
        CallTool<List<string>>("list_genres", new { }, ct);

    public Task<DatasetStats> GetStatsAsync(CancellationToken ct = default) =>
        CallTool<DatasetStats>("get_dataset_stats", new { }, ct);
}
