import asyncio
import logging
import httpx
import pandas as pd

logger = logging.getLogger(__name__)


async def embed_texts(
    texts: list[str],
    embedding_url: str,
    batch_size: int = 64,
) -> list[list[float]]:
    """
    Send texts to the embedding container in batches.
    Retries until the server is ready.
    Returns a flat list of embedding vectors.
    """
    all_embeddings: list[list[float]] = []

    async with httpx.AsyncClient(timeout=120) as client:
        # Wait for embedding server to be ready
        for attempt in range(30):
            try:
                r = await client.get(f"{embedding_url}/docs")
                if r.status_code == 200:
                    logger.info("Embedding server ready")
                    break
            except Exception:
                logger.info("Waiting for embedding server... attempt %d/30", attempt + 1)
                await asyncio.sleep(2)

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Send one at a time using /embed endpoint with {"input": text}
            for text in batch:
                response = await client.post(
                    f"{embedding_url}/embed",
                    json={"input": text},
                )
                response.raise_for_status()
                data = response.json()
                all_embeddings.append(data["embedding"])

            logger.info(
                "Embedded %d/%d records",
                min(i + batch_size, len(texts)),
                len(texts),
            )

    return all_embeddings


async def generate_embeddings(
    df: pd.DataFrame,
    embedding_url: str,
    batch_size: int = 64,
) -> pd.DataFrame:
    """Attach embedding vectors to the dataframe."""
    texts = df["augmented_text"].tolist()
    embeddings = await embed_texts(texts, embedding_url, batch_size)
    df["embedding"] = embeddings
    logger.info("Embeddings generated for %d records", len(df))
    return df
