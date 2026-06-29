import logging
import pandas as pd

logger = logging.getLogger(__name__)


def _budget_tier(budget: float) -> str:
    """Classify production budget into named tiers."""
    if budget < 1_000_000:
        return "micro"
    if budget < 10_000_000:
        return "low"
    if budget < 50_000_000:
        return "mid"
    if budget < 150_000_000:
        return "high"
    return "blockbuster"


def _decade(year: float) -> int | None:
    """Return the decade a film was released in (e.g. 1990)."""
    if pd.isna(year):
        return None
    return int(year // 10 * 10)


def _build_text(row: pd.Series) -> str:
    """Construct the rich text representation used for embedding."""
    return (
        f"Title: {row['Title']}\n"
        f"Genre: {row['Major Genre']}\n"
        f"Director: {row['Director']}\n"
        f"MPAA Rating: {row['MPAA Rating']}\n"
        f"Release Year: {row.get('Release Year', 'Unknown')}\n"
        f"Runtime: {row['Running Time min']:.0f} minutes\n"
        f"IMDB Rating: {row['IMDB Rating']:.1f}/10\n"
        f"Rotten Tomatoes: {row['Rotten Tomatoes Rating']:.0f}%\n"
        f"Budget: ${row['Production Budget']:,.0f}\n"
        f"Distributor: {row['Distributor']}\n"
        f"Creative Type: {row['Creative Type']}\n"
        f"Source: {row['Source']}\n"
        f"Budget Tier: {row['budget_tier']}\n"
        f"Decade: {row['decade']}"
    )


def augment(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features and the augmented text column."""
    df["budget_tier"] = df["Production Budget"].apply(_budget_tier)
    df["decade"] = df["Release Year"].apply(_decade)
    df["augmented_text"] = df.apply(_build_text, axis=1)

    logger.info("Augmentation complete — %d records", len(df))
    return df
