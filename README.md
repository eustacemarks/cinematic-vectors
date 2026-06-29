# Intelligent Movie Search Platform

An end-to-end semantic movie search platform built with Python, FastMCP, pgvector, and .NET 10. Ingests the Vega movies dataset, generates vector embeddings, and exposes natural language search via a secure REST API.

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        LOCAL (Docker Compose)                   │
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────────────┐  │
│  │  Data       │    │  Nomic       │    │  PostgreSQL 16     │  │
│  │  Pipeline   │───▶│  Embed v1.5  │    │  + pgvector        │  │
│  │  (Python)   │    │  :cpu        │    │                    │  │
│  │  clean/embed│    │  port 8001   │    │  vector(768)       │  │
│  └─────────────┘    └──────────────┘    │  HNSW index        │  │
│         │                               │  port 5432         │  │
│         └──────────────────────────────▶│                    │  │
│                                         └────────┬───────────┘  │
│                                                  │              │
│                                         ┌────────▼───────────┐  │
│                                         │  FastMCP Server    │  │
│                                         │  (Python)          │  │
│                                         │  SSE transport     │  │
│                                         │  port 8000         │  │
│                                         └────────┬───────────┘  │
│                                                  │              │
│                                         ┌────────▼───────────┐  │
│                                         │  .NET 10 Web API   │  │
│                                         │  JWT auth          │  │
│                                         │  OpenAPI/Swagger   │  │
│                                         │  port 8080         │  │
│                                         └────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Prometheus  │  │   Grafana    │  │        Jaeger        │   │
│  │  port 9090   │  │  port 3000   │  │      port 16686      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

               Flow: Pipeline → pgvector → MCP Server → .NET API → Client
               Observability spans all services
```

---

## 2. Prerequisites

| Tool | Version |
|------|---------|
| Docker Desktop | 4.x+ |
| Docker Compose | v2.x (bundled with Docker Desktop) |
| Git | any recent version |

> No local Python, .NET, or Node installation required — everything runs in containers.

For AWS deployment only:

| Tool | Version |
|------|---------|
| Terraform | >= 1.7 |
| AWS CLI | >= 2.x |

---

## 3. Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-username/movie-search-platform.git
cd movie-search-platform

# 2. Create environment file
cp .env.example .env
# Edit .env and set POSTGRES_PASSWORD and JWT_SECRET (JWT_SECRET must be 32+ characters)

# 3. Start the full platform
docker compose up --build

# 4. Obtain an auth token (in a new terminal, once pipeline finishes)
curl -s -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -d '{"ClientId":"movie-search","ClientSecret":"<your JWT_SECRET>","Role":"reader"}'

# 5. Search movies
curl -s "http://localhost:8080/api/v1/movies/search?q=sci-fi+films+directed+by+james+cameron" \
  -H "Authorization: Bearer <token>"
```

> The pipeline takes approximately 20–30 minutes on first run (embedding 3,201 records on CPU). Subsequent runs skip already-inserted records via `ON CONFLICT DO NOTHING`.

---

## 4. Service Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| .NET API | http://localhost:8080 | Public-facing REST API |
| Swagger UI | http://localhost:8080/swagger | Interactive API docs |
| OpenAPI Spec | http://localhost:8080/openapi/v1.json | Raw OpenAPI 3.1 spec |
| MCP Server | http://localhost:8000 | FastMCP SSE endpoint |
| MCP Health | http://localhost:8000/health | MCP server health check |
| PostgreSQL | localhost:5432 | pgvector database |
| Embedding Server | http://localhost:8001 | Nomic embed API |
| Prometheus | http://localhost:9090 | Metrics collection |
| Grafana | http://localhost:3000 | Dashboards (admin/admin) |
| Jaeger | http://localhost:16686 | Distributed tracing |

---

## 5. Data Pipeline

### How it works

The pipeline runs as a one-shot container (`movie_pipeline`) and executes these stages in sequence:

1. **Schema bootstrap** — creates the `movies` table and indexes in PostgreSQL if they don't exist
2. **Load** — fetches the Vega movies dataset (3,201 records)
3. **Clean** — removes duplicates, normalises strings, parses dates, clamps numeric ranges
4. **Impute** — fills missing values (see Data Decisions below)
5. **Augment** — constructs rich text representation + derived features (`budget_tier`, `decade`)
6. **Embed** — sends augmented text to the Nomic embedding server in batches
7. **Load** — upserts records into pgvector with `ON CONFLICT DO NOTHING`
8. **Report** — prints a JSON summary to stdout

### How to re-run

```bash
docker compose run pipeline
```

This is fully idempotent — re-running will not create duplicates.

### How to verify

```bash
# Check record count
docker exec movie_postgres psql -U movieuser -d moviedb \
  -c "SELECT COUNT(*) FROM movies;"

# Check a sample record
docker exec movie_postgres psql -U movieuser -d moviedb \
  -c "SELECT title, release_year, major_genre, imdb_rating FROM movies LIMIT 5;"

# Check embeddings are populated
docker exec movie_postgres psql -U movieuser -d moviedb \
  -c "SELECT COUNT(*) FROM movies WHERE embedding IS NOT NULL;"
```

---

## 6. Data Decisions

### Cleaning

| Issue | Action |
|-------|--------|
| Duplicate rows | Dropped with `drop_duplicates()` |
| String fields | Stripped whitespace, applied `.title()` casing |
| Release Date | Parsed to datetime, extracted `release_year` as integer |
| Negative budgets / impossible ratings | Clamped to `NULL` (treated as missing) |

### Imputation

| Field | Strategy | Rationale |
|-------|----------|-----------|
| `Director`, `Distributor`, `MPAA Rating`, `Major Genre`, `Creative Type`, `Source` | Fill with `"Unknown"` | Preserves the record for search without inferring meaning from sparse categorical data. `"Unknown"` is semantically meaningful in the embedding text. |
| `IMDB Rating`, `Rotten Tomatoes Rating`, `Running Time min`, `Production Budget` | Fill with column **median** | Median is robust to outliers (e.g. blockbuster budgets skewing the mean) and keeps imputed values within a plausible range for downstream embedding. |

### Derived Features

| Feature | Logic | Rationale |
|---------|-------|-----------|
| `budget_tier` | micro / low / mid / high / blockbuster based on budget thresholds | Provides a categorical signal for budget scale that embeds more naturally than a raw number |
| `decade` | `year // 10 * 10` | Enables decade-level filtering and improves era-based semantic queries |

---

## 7. Embedding Strategy

### Model

**Nomic Embed Text v1.5** (`mindthemath/nomic-embed-v1.5:cpu`)

- **Dimensionality**: 768
- **Why chosen**: Runs fully locally with no paid API, delivers strong semantic search quality, and is available as a pre-built Docker image with a simple HTTP API
- **Hardware**: CPU-only (no GPU required)

### Docker Compose wiring

The embedding server runs as its own container (`movie_embeddings`) on port 8080 internally (mapped to 8001 on the host). Both the pipeline and MCP server call it over the Docker network via `http://embeddings:8080/embed`.

```yaml
embeddings:
  image: mindthemath/nomic-embed-v1.5:cpu
  ports:
    - "8001:8080"
```

### Text construction

Each movie is converted to a structured text block before embedding:

```
Title: The Matrix
Genre: Action
Director: Lana Wachowski
MPAA Rating: R
Release Year: 1999
Runtime: 136 minutes
IMDB Rating: 8.7/10
Rotten Tomatoes: 88%
Budget: $63,000,000
Distributor: Warner Bros.
Creative Type: Science Fiction
Source: Original Screenplay
Budget Tier: high
Decade: 1990
```

### API contract

```
POST http://embeddings:8080/embed
{"input": "text to embed"}

Response: {"embedding": [0.123, -0.456, ...]}  # 768 floats
```

---

## 8. MCP Server

The FastMCP server exposes five tools over SSE transport, also accessible via a REST shim at `POST /mcp/tool`.

### Available tools

| Tool | Description |
|------|-------------|
| `search_movies_by_description` | Semantic vector search with optional filters (genre, IMDB rating, MPAA rating, decade) |
| `get_movie_by_title` | Exact or fuzzy title lookup |
| `get_similar_movies` | Returns movies most similar to a given movie ID |
| `list_genres` | Returns all distinct genres in the dataset |
| `get_dataset_stats` | Summary statistics (count, avg ratings, year range, genres) |

### Testing tools directly

```bash
# Search
curl -s -X POST http://localhost:8000/mcp/tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_movies_by_description",
    "arguments": {"query": "dark psychological thriller", "top_k": 3}
  }' | python3 -m json.tool

# List genres
curl -s -X POST http://localhost:8000/mcp/tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "list_genres", "arguments": {}}' | python3 -m json.tool

# Dataset stats
curl -s -X POST http://localhost:8000/mcp/tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_dataset_stats", "arguments": {}}' | python3 -m json.tool

# Health check
curl http://localhost:8000/health
```

---

## 9. API Documentation

All endpoints require a Bearer token except `/health` and `/auth/token`.

### Authentication

```bash
curl -s -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -d '{"ClientId":"movie-search","ClientSecret":"<JWT_SECRET>","Role":"reader"}'
```

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

### GET /health

```bash
curl http://localhost:8080/health
```

```json
{"status": "ok"}
```

### GET /api/v1/movies/search

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | ✅ | Natural language search query |
| `top_k` | int | ❌ | Number of results (default 10, max 50) |
| `genre` | string | ❌ | Filter by genre |
| `min_imdb_rating` | float | ❌ | Minimum IMDB rating |
| `mpaa_rating` | string | ❌ | Filter by MPAA rating |
| `decade` | int | ❌ | Filter by decade (e.g. 1990) |

```bash
curl -s "http://localhost:8080/api/v1/movies/search?q=animated+family+movies+by+disney&top_k=3" \
  -H "Authorization: Bearer $TOKEN"
```

```json
[
  {
    "id": "373d2cdc-...",
    "title": "Chicken Little",
    "releaseYear": 2005,
    "majorGenre": "Adventure",
    "mpaaRating": "G",
    "director": "Mark Dindal",
    "distributor": "Walt Disney Pictures",
    "imdbRating": 5.8,
    "rtRating": 36,
    "productionBudget": 60000000,
    "runningTimeMin": 80,
    "budgetTier": "high",
    "decade": 2000,
    "similarity": 0.6796
  }
]
```

### GET /api/v1/movies/{id}

```bash
curl -s "http://localhost:8080/api/v1/movies/373d2cdc-94e9-4a58-809d-25b1b38bdcad" \
  -H "Authorization: Bearer $TOKEN"
```

### GET /api/v1/movies/{id}/similar

```bash
curl -s "http://localhost:8080/api/v1/movies/373d2cdc-94e9-4a58-809d-25b1b38bdcad/similar" \
  -H "Authorization: Bearer $TOKEN"
```

### GET /api/v1/movies/genres

```bash
curl -s "http://localhost:8080/api/v1/movies/genres" \
  -H "Authorization: Bearer $TOKEN"
```

```json
["Action", "Adventure", "Comedy", "Drama", "Horror", ...]
```

### GET /api/v1/stats

```bash
curl -s "http://localhost:8080/api/v1/stats" \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "totalMovies": 3191,
  "genres": ["Action", "Adventure", ...],
  "avgImdbRating": 6.29,
  "avgRtRating": 54.54,
  "earliestYear": 1928,
  "latestYear": 2046
}
```

---

## 10. Authentication

The API uses JWT Bearer tokens via a client credentials flow.

### Obtaining a token

```bash
curl -s -X POST http://localhost:8080/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "ClientId": "movie-search",
    "ClientSecret": "<your JWT_SECRET from .env>",
    "Role": "reader"
  }'
```

Roles: `reader` (search endpoints) or `admin` (all endpoints including stats).

Tokens expire after **8 hours**.

### Using a token

```bash
export TOKEN="eyJhbGci..."

curl -s "http://localhost:8080/api/v1/movies/search?q=action" \
  -H "Authorization: Bearer $TOKEN"
```

### Via Swagger UI

1. Open http://localhost:8080/swagger
2. Click **Authorize** (padlock icon)
3. Enter `Bearer <your_token>`
4. All subsequent requests will include the token automatically

---

## 11. Observability

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f mcp-server
docker compose logs -f pipeline
```

Logs are structured JSON from the .NET API (Serilog) and plain text from the Python services.

### Metrics — Prometheus

Open http://localhost:9090

Prometheus scrapes:
- `.NET API` at `api:8080/metrics`
- `MCP Server` at `mcp-server:8000/metrics`

Example queries:
```
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])
```

### Dashboards — Grafana

Open http://localhost:3000 (username: `admin`, password: value of `GRAFANA_PASSWORD` in `.env`, default `admin`)

The Prometheus datasource is pre-provisioned. Import a dashboard or build one with:
- Request rate & latency (p50/p95/p99)
- Error rate
- Active connections

### Distributed Traces — Jaeger

Open http://localhost:16686

The .NET API exports OpenTelemetry traces to Jaeger. Select service `movie-search-api` and search for traces to inspect end-to-end request flow including MCP tool call latency.

---

## 12. Terraform Deployment (AWS)

### Prerequisites

- AWS account with appropriate IAM permissions
- Terraform >= 1.7 installed
- AWS CLI configured (`aws configure`)
- S3 bucket and DynamoDB table for Terraform state (create once):

```bash
aws s3 mb s3://movie-search-tfstate --region us-east-1
aws dynamodb create-table \
  --table-name movie-search-tflock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Step-by-step deployment

```bash
# 1. Build and push images to ECR (CI/CD does this automatically)
cd terraform
terraform init

# 2. Create a terraform.tfvars file for dev
cat > environments/dev/terraform.tfvars <<EOF
environment       = "dev"
vpc_cidr          = "10.0.0.0/16"
aws_region        = "us-east-1"
EOF

# 3. Plan (review what will be created)
terraform plan \
  -var-file=environments/dev/terraform.tfvars \
  -var="postgres_password=<secure_password>" \
  -var="jwt_secret=<secure_jwt_secret_32_chars_minimum>"

# 4. Apply dev environment
terraform apply \
  -var-file=environments/dev/terraform.tfvars \
  -var="postgres_password=<secure_password>" \
  -var="jwt_secret=<secure_jwt_secret_32_chars_minimum>"

# 5. Get the ALB DNS name
terraform output alb_dns_name

# 6. Apply prod (after manual approval)
terraform apply \
  -var-file=environments/prod/terraform.tfvars \
  -var="postgres_password=<secure_password>" \
  -var="jwt_secret=<secure_jwt_secret_32_chars_minimum>"
```

### Infrastructure overview

| Resource | Details |
|----------|---------|
| Compute | ECS Fargate (serverless containers) |
| Database | RDS PostgreSQL 16 in private subnets |
| Load Balancer | ALB with HTTPS (ACM certificate) |
| Secrets | AWS Secrets Manager |
| Container Registry | ECR (one repo per service) |
| Networking | VPC with public/private subnets, NAT gateway |
| Monitoring | CloudWatch + X-Ray |
| State | S3 backend with DynamoDB locking |

### Secrets management

All credentials are stored in AWS Secrets Manager — never hardcoded. ECS tasks pull secrets at runtime via IAM roles. No access keys are used.

### Tear down

```bash
terraform destroy \
  -var-file=environments/dev/terraform.tfvars \
  -var="postgres_password=x" \
  -var="jwt_secret=x"
```

---

## 13. Running Tests

### Python unit tests (pipeline + MCP server)

```bash
docker compose run --rm pipeline pytest /app/tests/ -v
docker compose run --rm mcp-server pytest /app/tests/ -v
```

Or locally:

```bash
cd pipeline && pip install -e ".[dev]" && pytest tests/ -v
cd mcp-server && pip install -e ".[dev]" && pytest tests/ -v
```

### .NET unit tests

```bash
cd api
dotnet test MovieSearch.sln -v normal
```

Or via Docker:

```bash
docker build -t movie-search-api-test ./api
docker run --rm movie-search-api-test dotnet test
```

### Integration tests

```bash
# Full stack must be running
docker compose up -d

# Run integration test suite
docker compose run pipeline pytest tests/integration/ -v
```

### Load tests

A k6 load test script is provided at `scripts/load_test.js`:

```bash
# Install k6 (macOS)
brew install k6

# Run load test against search endpoint (requires running stack + valid token)
export TOKEN="<your_token>"
k6 run scripts/load_test.js
```
