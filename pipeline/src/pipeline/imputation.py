import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Categorical fields: fill with "Unknown" — preserves the record for search
# without inferring meaning from sparse data.
CATEGORICAL_UNKNOWN = ["Director", "Distributor", "MPAA Rating",
                       "Major Genre", "Creative Type", "Source"]

# Numeric fields: fill with column median — robust to outliers and keeps
# the value in a plausible range for downstream embedding text.
NUMERIC_MEDIAN = ["IMDB Rating", "Rotten Tomatoes Rating",
                  "Running Time min", "Production Budget"]


def impute(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Fill missing values.
    Returns imputed dataframe and a report of counts filled per column.
    """
    report: dict = {}

    for col in CATEGORICAL_UNKNOWN:
        if col not in df.columns:
            continue
        n = int(df[col].isna().sum())
        df[col] = df[col].fillna("Unknown")
        report[col] = n

    for col in NUMERIC_MEDIAN:
        if col not in df.columns:
            continue
        n = int(df[col].isna().sum())
        median = df[col].median()
        df[col] = df[col].fillna(median)
        report[col] = n

    logger.info("Imputation complete: %s", report)
    return df, report
