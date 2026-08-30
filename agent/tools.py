import pandas as pd
import logging

logger = logging.getLogger(__name__)

def filter_deals(deals_df: pd.DataFrame, quality_reports: list, sector=None, stage=None, quarter=None) -> dict:
    """
    Filters deals dataset by sector, stage, or quarter.
    """
    df = deals_df.copy()
    if sector and str(sector).lower() != "none" and str(sector).strip() != "":
        df = df[df["sector"].astype(str).str.lower() == str(sector).lower().strip()]
    if stage and str(stage).lower() != "none" and str(stage).strip() != "":
        df = df[df["deal_stage"].astype(str).str.lower() == str(stage).lower().strip()]
    if quarter and str(quarter).lower() != "none" and str(quarter).strip() != "":
        # Extract calendar quarters from close_date
        df = df[df["close_date"].notna()]
        df["quarter_temp"] = df["close_date"].dt.quarter.apply(lambda x: f"q{x}")
        df = df[df["quarter_temp"].astype(str) == str(quarter).lower().strip()]
        df = df.drop(columns=["quarter_temp"])

    caveats = _extract_quality_caveats(quality_reports, "Deals Board")
    return {
        "data": df,
        "caveats": caveats
    }

def filter_work_orders(wo_df: pd.DataFrame, quality_reports: list, status=None, customer=None) -> dict:
    """
    Filters work orders dataset by status or customer name code.
    """
    df = wo_df.copy()
    if status and str(status).lower() != "none" and str(status).strip() != "":
        df = df[df["execution_status"].astype(str).str.lower() == str(status).lower().strip()]
    if customer and str(customer).lower() != "none" and str(customer).strip() != "":
        df = df[df["customer_name_code"].astype(str).str.lower() == str(customer).lower().strip()]

    caveats = _extract_quality_caveats(quality_reports, "Work Orders Board")
    return {
        "data": df,
        "caveats": caveats
    }

def join_deals_and_orders(deals_df: pd.DataFrame, wo_df: pd.DataFrame, deals_reports: list, wo_reports: list) -> dict:
    """
    Joins Deals and Work Orders boards on matching deal name fields.
    """
    if deals_df.empty or wo_df.empty:
        return {"data": pd.DataFrame(), "caveats": "Cannot join; empty boards."}

    merged = pd.merge(
        deals_df,
        wo_df,
        left_on="name",
        right_on="deal_name",
        suffixes=("_deal", "_wo")
    )
    
    caveats = _extract_quality_caveats(deals_reports + wo_reports, "Joined Boards")
    return {
        "data": merged,
        "caveats": caveats
    }

def aggregate(df: pd.DataFrame, quality_reports: list, group_by: str, metric: str, agg_func: str = "sum") -> dict:
    """
    Aggregates pandas DataFrame grouped by a key.
    """
    if df.empty:
        return {"data": pd.DataFrame(), "caveats": "Empty DataFrame."}

    if group_by not in df.columns:
        raise ValueError(f"Grouping column '{group_by}' does not exist.")
    if metric not in df.columns:
        raise ValueError(f"Metric column '{metric}' does not exist.")

    agg_func = agg_func.lower().strip()
    if agg_func not in ("sum", "mean", "count"):
        agg_func = "sum"

    # Fill NA before grouping to prevent group dropping
    df_temp = df.copy()
    df_temp[group_by] = df_temp[group_by].fillna("Unknown")

    grouped = df_temp.groupby(group_by)[metric].agg(agg_func).reset_index()
    grouped.columns = [group_by, f"{agg_func}_of_{metric}"]

    caveats = _extract_quality_caveats(quality_reports, f"Aggregation on {group_by}")
    return {
        "data": grouped,
        "caveats": caveats
    }

def generate_leadership_summary(deals_df: pd.DataFrame, wo_df: pd.DataFrame, deals_reports: list, wo_reports: list) -> dict:
    """
    Pulls key high-level operational BI metrics from both boards.
    """
    # 1. Pipeline value by Sector
    pipeline_sector = pd.DataFrame()
    if not deals_df.empty and "sector" in deals_df.columns and "deal_value" in deals_df.columns:
        pipeline_sector = deals_df.groupby("sector")["deal_value"].sum().reset_index()

    # 2. WO execution status completion rate
    completed_wo = 0
    total_wo = len(wo_df)
    completion_rate = 0.0
    if total_wo > 0 and "execution_status" in wo_df.columns:
        completed_wo = (wo_df["execution_status"].astype(str).str.lower() == "completed").sum()
        completion_rate = (completed_wo / total_wo) * 100.0

    # 3. Revenue realized vs billed
    total_billed = 0.0
    total_collected = 0.0
    if not wo_df.empty:
        if "billed_excl_gst" in wo_df.columns:
            total_billed = wo_df["billed_excl_gst"].sum()
        if "collected_incl_gst" in wo_df.columns:
            total_collected = wo_df["collected_incl_gst"].sum()

    # Consolidate raw facts
    stats = {
        "total_deals_count": len(deals_df),
        "total_deals_value": deals_df["deal_value"].sum() if "deal_value" in deals_df.columns else 0.0,
        "pipeline_by_sector": pipeline_sector.to_dict(orient="records"),
        "total_work_orders": total_wo,
        "work_order_completion_rate": f"{completion_rate:.1f}% ({completed_wo}/{total_wo})",
        "revenue_billed_excl_gst": total_billed,
        "revenue_collected_incl_gst": total_collected
    }

    caveats = _extract_quality_caveats(deals_reports + wo_reports, "Leadership BI Report")
    return {
        "stats": stats,
        "caveats": caveats
    }

def _extract_quality_caveats(reports: list, context_name: str) -> str:
    if not reports:
        return "No significant missing values flagged."
    
    # Filter to build clean short warning logs
    warnings = []
    for r in reports:
        if any(keyword in r.lower() for keyword in ["close date", "due date", "deal name", "value", "status"]):
            warnings.append(r)
            
    if not warnings:
        warnings = reports[:2]
        
    return f"Caveats ({context_name}): " + " | ".join(warnings[:3])
