import pandas as pd

def check_data_quality(df: pd.DataFrame, board_name: str) -> dict:
    """
    Scans a normalized DataFrame and returns details about data shape,
    missing value rates, and data quality flags/warnings.
    """
    total_rows = len(df)
    missing_percentages = {}
    quality_flags = []

    if total_rows == 0:
        return {
            "name": board_name,
            "total_rows": 0,
            "missing_percentages": {},
            "quality_flags": ["Table is empty."]
        }

    # Analyze missing/empty elements
    for col in df.columns:
        # Match NaN/NaT/None string values
        missing_mask = df[col].isna() | (df[col] == "None") | (df[col].astype(str) == "NaT") | (df[col] == "")
        missing_count = missing_mask.sum()
        pct = (missing_count / total_rows) * 100
        missing_percentages[col] = f"{pct:.1f}%"

        # Check for specific column issues
        if col in ["close_date", "due_date"] and pct > 40:
            quality_flags.append(f"More than 40% of date values in '{col}' are missing.")
        if col == "deal_name" and pct > 30:
            quality_flags.append(f"More than 30% of work orders are not linked to a deal.")

    # Business rule validation
    if "value" in df.columns:
        negative_deals = (df["value"] < 0).sum()
        if negative_deals > 0:
            quality_flags.append(f"{negative_deals} deal(s) have negative monetary values.")
            
        zero_deals = (df["value"] == 0).sum()
        if zero_deals > 0:
            quality_flags.append(f"{zero_deals} deal(s) have 0.0 value.")

    return {
        "name": board_name,
        "total_rows": total_rows,
        "missing_percentages": missing_percentages,
        "quality_flags": quality_flags
    }
