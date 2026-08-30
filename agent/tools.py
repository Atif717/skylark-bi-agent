import pandas as pd
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def filter_deals(
    deals_df: pd.DataFrame,
    quality_reports: list,
    sector: Optional[str] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    quarter: Optional[str] = None
) -> dict:
    """
    Filters deals dataset by sector, stage, deal status, or calendar quarter.
    """
    df = deals_df.copy()

    if sector and str(sector).lower() != "none" and str(sector).strip() != "":
        if "sector" in df.columns:
            df = df[df["sector"].astype(str).str.lower() == str(sector).lower().strip()]

    if stage and str(stage).lower() != "none" and str(stage).strip() != "":
        if "deal_stage" in df.columns:
            df = df[df["deal_stage"].astype(str).str.lower().str.contains(str(stage).lower().strip(), na=False)]

    if status and str(status).lower() != "none" and str(status).strip() != "":
        if "deal_status" in df.columns:
            df = df[df["deal_status"].astype(str).str.lower() == str(status).lower().strip()]

    if quarter and str(quarter).lower() != "none" and str(quarter).strip() != "":
        # Flexible quarter parsing checking close_date or tentative_close_date
        date_col = None
        for candidate in ["close_date", "tentative_close_date", "created_date"]:
            if candidate in df.columns and df[candidate].notna().any():
                date_col = candidate
                break

        if date_col:
            df = df[df[date_col].notna()].copy()
            q_target = str(quarter).lower().replace("q", "").strip()
            if q_target.isdigit():
                df = df[df[date_col].dt.quarter == int(q_target)]

    caveats = _extract_quality_caveats(quality_reports, "Deals Board")
    return {
        "data": df,
        "caveats": caveats
    }


def filter_work_orders(
    wo_df: pd.DataFrame,
    quality_reports: list,
    status: Optional[str] = None,
    customer: Optional[str] = None,
    sector: Optional[str] = None
) -> dict:
    """
    Filters work orders dataset by status, customer name code, or sector.
    """
    df = wo_df.copy()

    if status and str(status).lower() != "none" and str(status).strip() != "":
        target_status = str(status).lower().strip()
        if "execution_status" in df.columns:
            if target_status == "ongoing":
                df = df[df["execution_status"].astype(str).str.lower().isin(["ongoing", "executed until current month"])]
            else:
                df = df[df["execution_status"].astype(str).str.lower().str.contains(target_status, na=False)]

    if customer and str(customer).lower() != "none" and str(customer).strip() != "":
        if "customer_name_code" in df.columns:
            df = df[df["customer_name_code"].astype(str).str.lower() == str(customer).lower().strip()]

    if sector and str(sector).lower() != "none" and str(sector).strip() != "":
        if "sector" in df.columns:
            df = df[df["sector"].astype(str).str.lower() == str(sector).lower().strip()]

    caveats = _extract_quality_caveats(quality_reports, "Work Orders Board")
    return {
        "data": df,
        "caveats": caveats
    }


def join_deals_and_orders(deals_df: pd.DataFrame, wo_df: pd.DataFrame, deals_reports: list, wo_reports: list, **kwargs) -> dict:
    """
    Joins Deals and Work Orders boards on the common entity name ('name').
    """
    if deals_df.empty or wo_df.empty:
        return {"data": pd.DataFrame(), "caveats": "Cannot join; empty boards."}

    d = deals_df.copy()
    w = wo_df.copy()

    # Join on the common entity name
    merged = pd.merge(
        d,
        w,
        on="name",
        how="inner",
        suffixes=("_deal", "_wo")
    )

    # If the user asked for ongoing work orders or open deals, filter gracefully:
    # (Checking if filters were passed via kwargs or filtering directly)
    if "deal_status" in merged.columns:
        # Keep open deals if specified in kwargs
        deal_status_filter = kwargs.get("deal_status")
        if deal_status_filter:
            merged = merged[merged["deal_status"].astype(str).str.lower() == str(deal_status_filter).lower().strip()]

    if "execution_status" in merged.columns:
        exec_filter = kwargs.get("execution_status") or kwargs.get("status")
        if exec_filter:
            tgt = str(exec_filter).lower().strip()
            if tgt == "ongoing":
                merged = merged[merged["execution_status"].astype(str).str.lower().isin(["ongoing", "executed until current month"])]
            else:
                merged = merged[merged["execution_status"].astype(str).str.lower().str.contains(tgt, na=False)]

    # Select clean representative columns for UI display
    cols_to_show = [
        col for col in [
            "name", "deal_status", "execution_status", "deal_value",
            "amount_excl_gst", "sector_deal", "owner_code", "customer_name_code"
        ] if col in merged.columns
    ]

    display_df = merged[cols_to_show] if cols_to_show else merged

    caveats = _extract_quality_caveats(deals_reports + wo_reports, "Joined Boards")
    return {
        "data": display_df,
        "caveats": caveats
    }

def aggregate(
    df: pd.DataFrame,
    quality_reports: list,
    group_by: str,
    metric: str,
    agg_func: str = "sum"
) -> dict:
    """
    Aggregates pandas DataFrame grouped by a key.
    """
    if df.empty:
        return {"data": pd.DataFrame(), "caveats": "Empty DataFrame."}

    # Normalize column names for flexible matching
    col_map = {col.lower().strip(): col for col in df.columns}
    gb_key = col_map.get(group_by.lower().strip())
    metric_key = col_map.get(metric.lower().strip())

    if not gb_key:
        raise ValueError(f"Grouping column '{group_by}' does not exist.")
    if not metric_key:
        raise ValueError(f"Metric column '{metric}' does not exist.")

    agg_func = agg_func.lower().strip()
    if agg_func not in ("sum", "mean", "count"):
        agg_func = "sum"

    # Fill NA before grouping to prevent dropping groups
    df_temp = df.copy()
    df_temp[gb_key] = df_temp[gb_key].fillna("Unknown")

    grouped = df_temp.groupby(gb_key)[metric_key].agg(agg_func).reset_index()
    grouped.columns = [gb_key, f"{agg_func}_of_{metric_key}"]

    caveats = _extract_quality_caveats(quality_reports, f"Aggregation on {group_by}")
    return {
        "data": grouped,
        "caveats": caveats
    }


def generate_leadership_summary(
    deals_df: pd.DataFrame,
    wo_df: pd.DataFrame,
    deals_reports: list,
    wo_reports: list
) -> dict:
    """
    Pulls key high-level operational BI metrics from both boards.
    """
    # 1. Pipeline value by Sector
    pipeline_sector = pd.DataFrame()
    if not deals_df.empty and "sector" in deals_df.columns and "deal_value" in deals_df.columns:
        pipeline_sector = (
            deals_df.groupby("sector")["deal_value"]
            .sum()
            .reset_index()
            .sort_values(by="deal_value", ascending=False)
        )

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
        "revenue_collected_incl_gst": total_collected,
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