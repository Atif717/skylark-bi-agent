import pandas as pd

def check_data_quality(df: pd.DataFrame, board_name: str) -> dict:
    """
    Computes data quality statistics for a cleaned dataframe.
    Identifies the percentage of missing or coerced values (None, NaT, NaN).
    """
    total_rows = len(df)
    missing_percentages = {}
    reports = []

    if total_rows == 0:
        return {
            "name": board_name,
            "total_rows": 0,
            "missing_percentages": {},
            "reports": ["Table is empty."]
        }

    for col in df.columns:
        if col in ("item_id", "id"):
            continue
        
        # Check standard NaNs, NaTs, "None" text values, or empty strings
        missing_mask = (
            df[col].isna() | 
            (df[col].astype(str) == "None") | 
            (df[col].astype(str) == "NaT") | 
            (df[col].astype(str).str.strip() == "")
        )
        
        missing_count = missing_mask.sum()
        pct = (missing_count / total_rows) * 100
        missing_percentages[col] = pct

        if pct > 0:
            friendly_name = col.replace("_", " ").title()
            reports.append(f"{pct:.1f}% of {friendly_name} were missing/unparseable.")

    return {
        "name": board_name,
        "total_rows": total_rows,
        "missing_percentages": missing_percentages,
        "reports": reports
    }
