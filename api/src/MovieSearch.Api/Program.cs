using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Serilog;
using MovieSearch.Domain;
using MovieSearch.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

// ── Serilog ───────────────────────────────────────────────────────────────────
builder.Host.UseSerilog((ctx, cfg) =>
    cfg.ReadFrom.Configuration(ctx.Configuration)
       .WriteTo.Console(outputTemplate:
           "[{Timestamp:HH:mm:ss} {Level:u3}] {Message:lj}{NewLine}{Exception}"));

// ── JWT Auth ──────────────────────────────────────────────────────────────────
var jwtSecret = builder.Configuration["JWT_SECRET"]
    ?? throw new InvalidOperationException("JWT_SECRET is required");

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(opt =>
    {
        opt.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuerSigningKey = true,
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtSecret)),
            ValidateIssuer = false,
            ValidateAudience = false,
        };
    });
builder.Services.AddAuthorization();

// ── MCP HTTP client ───────────────────────────────────────────────────────────
var mcpUrl = builder.Configuration["MCP_SERVER_URL"] ?? "http://mcp-server:8000";
builder.Services.AddHttpClient<IMovieSearchService, McpMovieSearchService>(c =>
{
    c.BaseAddress = new Uri(mcpUrl);
    c.Timeout = TimeSpan.FromSeconds(30);
});

// ── OpenTelemetry ─────────────────────────────────────────────────────────────
builder.Services.AddOpenTelemetry()
    .ConfigureResource(r => r.AddService("movie-search-api"))
    .WithTracing(t => t
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddJaegerExporter(o =>
        {
            o.Endpoint = new Uri(
                builder.Configuration["OTEL_EXPORTER_JAEGER_ENDPOINT"]
                ?? "http://jaeger:14268/api/traces");
        }));

// ── Swagger ───────────────────────────────────────────────────────────────────
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(c =>
{
    c.SwaggerDoc("v1", new OpenApiInfo { Title = "Movie Search API", Version = "v1" });
    c.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Type = SecuritySchemeType.Http,
        Scheme = "bearer",
    });
    c.AddSecurityRequirement(new OpenApiSecurityRequirement
    {
        [new OpenApiSecurityScheme
        {
            Reference = new OpenApiReference { Type = ReferenceType.SecurityScheme, Id = "Bearer" }
        }] = []
    });
});

builder.Services.AddOutputCache();

var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();
app.UseOutputCache();
app.UseSwagger();
app.UseSwaggerUI();

// ── Health ────────────────────────────────────────────────────────────────────
app.MapGet("/health", () => Results.Ok(new { status = "ok" }))
   .AllowAnonymous();

// ── Auth token (client credentials) ──────────────────────────────────────────
app.MapPost("/auth/token", (TokenRequest req) =>
{
    if (req.ClientId == "movie-search" && req.ClientSecret == jwtSecret)
    {
        var token = JwtHelper.Generate(jwtSecret, req.Role ?? "reader");
        return Results.Ok(new { access_token = token, token_type = "bearer" });
    }
    return Results.Unauthorized();
}).AllowAnonymous();

// ── Movie endpoints ───────────────────────────────────────────────────────────
var api = app.MapGroup("/api/v1").RequireAuthorization();

api.MapGet("/movies/search", async (
    string q,
    IMovieSearchService svc,
    int top_k = 10,
    string? genre = null,
    double? min_imdb_rating = null,
    string? mpaa_rating = null,
    int? decade = null,
    CancellationToken ct = default) =>
{
    var results = await svc.SearchAsync(
        new MovieSearchQuery(q, Math.Min(top_k, 50), genre, min_imdb_rating, mpaa_rating, decade), ct);
    return Results.Ok(results);
}).CacheOutput(p => p.Expire(TimeSpan.FromMinutes(5)));

api.MapGet("/movies/genres", async (IMovieSearchService svc, CancellationToken ct) =>
    Results.Ok(await svc.ListGenresAsync(ct)));

api.MapGet("/movies/{id}", async (string id, IMovieSearchService svc, CancellationToken ct) =>
{
    var movie = await svc.GetByIdAsync(id, ct);
    return movie is null ? Results.NotFound() : Results.Ok(movie);
});

api.MapGet("/movies/{id}/similar", async (string id, IMovieSearchService svc, CancellationToken ct) =>
    Results.Ok(await svc.GetSimilarAsync(id, ct: ct)));

api.MapGet("/stats", async (IMovieSearchService svc, CancellationToken ct) =>
    Results.Ok(await svc.GetStatsAsync(ct)));

app.Run();

record TokenRequest(string ClientId, string ClientSecret, string? Role);
