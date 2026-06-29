import logging
import pandas as pd

logger = logging.getLogger(__name__)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean the raw movies dataset.
    Returns cleaned dataframe and a report of actions taken.
    """
    report: dict = {}
    original_len = len(df)

    # Normalise column names — vega_datasets uses underscores, raw JSON uses spaces
    df.columns = [c.replace("_", " ") for c in df.columns]

    # Drop exact duplicates
    df = df.drop_duplicates()
    report["duplicates_removed"] = original_len - len(df)

    # Normalise string columns: strip whitespace, consistent casing
    str_cols = ["Title", "Distributor", "Director", "Major Genre",
                "Creative Type", "Source", "MPAA Rating"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].str.strip().str.title()

    # Parse Release Date → datetime, extract year
    if "Release Date" in df.columns:
        df["Release Date"] = pd.to_datetime(df["Release Date"], errors="coerce")
        df["Release Year"] = df["Release Date"].dt.year.astype("Int64")
        report["invalid_dates"] = int(df["Release Date"].isna().sum())

    # Clamp numeric fields to sensible ranges
    numeric_clamps = {
        "IMDB Rating": (0, 10),
        "Rotten Tomatoes Rating": (0, 100),
        "Running Time min": (1, 600),
        "Production Budget": (0, None),
        "US Gross": (0, None),
        "Worldwide Gross": (0, None),
    }
    for col, (low, high) in numeric_clamps.items():
        if col not in df.columns:
            continue
        before = df[col].notna().sum()
        if low is not None:
            df.loc[df[col] < low, col] = pd.NA
        if high is not None:
            df.loc[df[col] > high, col] = pd.NA
        report[f"{col}_clamped"] = int(before - df[col].notna().sum())

    logger.info("Cleaning complete: %s", report)
    return df, report
