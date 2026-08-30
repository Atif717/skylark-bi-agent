import pandas as pd
import logging

logger = logging.getLogger(__name__)

def query_deals(deals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the loaded Deals dataframe.
    """
    return deals_df

def query_work_orders(wo_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the loaded Work Orders dataframe.
    """
    return wo_df

def join_boards(deals_df: pd.DataFrame, wo_df: pd.DataFrame) -> pd.DataFrame:
    """
    Combines Deals and Work Orders boards on matching deal name fields.
    """
    if deals_df.empty or wo_df.empty:
        logger.warning("One or both dataframes are empty; returning empty merged dataframe.")
        return pd.DataFrame()

    # Join Deals.name -> WorkOrders.deal_name
    merged = pd.merge(
        deals_df,
        wo_df,
        left_on="name",
        right_on="deal_name",
        suffixes=("_deal", "_wo")
    )
    return merged

def aggregate_metrics(deals_df: pd.DataFrame, wo_df: pd.DataFrame, dataset: str, group_by: str, agg_col: str, agg_func: str) -> pd.DataFrame:
    """
    Aggregates metrics for either deals or work_orders based on requested grouping columns.
    """
    df = deals_df if dataset.lower() == "deals" else wo_df

    if df.empty:
        logger.warning(f"Dataset '{dataset}' is empty. Cannot aggregate.")
        return pd.DataFrame()

    if group_by not in df.columns:
        raise ValueError(f"Column '{group_by}' does not exist in dataset '{dataset}'. "
                         f"Available columns: {list(df.columns)}")

    if agg_col not in df.columns:
        raise ValueError(f"Column '{agg_col}' does not exist in dataset '{dataset}'. "
                         f"Available columns: {list(df.columns)}")

    # Handle standard aggregations
    agg_func = agg_func.lower()
    if agg_func not in ("sum", "mean", "count"):
        raise ValueError(f"Aggregation function '{agg_func}' not supported. Choose sum, mean, or count.")

    grouped = df.groupby(group_by)[agg_col].agg(agg_func).reset_index()
    # Provide a clean column header for aggregation result
    grouped.columns = [group_by, f"{agg_func}_of_{agg_col}"]
    return grouped
