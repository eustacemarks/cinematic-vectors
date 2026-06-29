import os


def dsn() -> str:
    return (
        f"postgresql://{os.environ['POSTGRES_USER']}"
        f":{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ.get('POSTGRES_HOST', 'localhost')}"
        f":5432/{os.environ['POSTGRES_DB']}"
    )


EMBEDDING_URL: str = os.environ.get("EMBEDDING_URL", "http://embeddings:8001")
MCP_PORT: int = int(os.environ.get("MCP_PORT", "8000"))
