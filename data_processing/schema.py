# Schema mapping for Deals and Work Orders boards
# Maps raw Monday column IDs -> friendly field names

DEALS_SCHEMA = {
    "owner_code": "owner_code",
    "client_code": "client_code",
    "deal_status": "deal_status",
    "close_date_a": "close_date",
    "closure_probability": "closure_probability",
    "masked_deal_value": "deal_value",
    "tentative_close_date": "tentative_close_date",
    "deal_stage": "deal_stage",
    "product_deal": "product",
    "sector_service": "sector",
    "created_date": "created_date"
}

WORK_ORDERS_SCHEMA = {
    "deal_name_masked": "deal_name",
    "customer_name_code": "customer_name_code",
    "nature_of_work": "nature_of_work",
    "last_executed_month": "last_executed_month",
    "execution_status": "execution_status",
    "data_delivery_date": "data_delivery_date",
    "date_of_po": "date_of_po",
    "document_type": "document_type",
    "probable_start_date": "probable_start_date",
    "probable_end_date": "probable_end_date",
    "bd_kam_code": "bd_kam_code",
    "sector": "sector",
    "type_of_work": "type_of_work",
    "skylark_software_part": "skylark_software_part",
    "last_invoice_date": "last_invoice_date",
    "latest_invoice_no": "latest_invoice_no",
    "amount_excl_gst": "amount_excl_gst",
    "amount_incl_gst": "amount_incl_gst",
    "billed_excl_gst": "billed_excl_gst",
    "billed_incl_gst": "billed_incl_gst",
    "collected_incl_gst": "collected_incl_gst",
    "to_be_billed_excl_gst": "to_be_billed_excl_gst",
    "to_be_billed_incl_gst": "to_be_billed_incl_gst",
    "amount_receivable": "amount_receivable",
    "ar_priority_account": "ar_priority_account",
    "quantity_by_ops": "quantity_by_ops",
    "quantities_per_po": "quantities_per_po",
    "quantity_billed": "quantity_billed",
    "balance_quantity": "balance_quantity",
    "invoice_status": "invoice_status",
    "expected_billing_month": "expected_billing_month",
    "actual_billing_month": "actual_billing_month",
    "actual_collection_month": "actual_collection_month",
    "wo_status_billed": "wo_status_billed",
    "collection_status": "collection_status",
    "collection_date": "collection_date",
    "billing_status": "billing_status"
}

def map_columns(items: list, schema: dict) -> list:
    """
    Translates list of flat dicts with raw Monday column IDs into friendly keys.
    """
    mapped_items = []
    for item in items:
        mapped = {
            "item_id": item.get("id"),
            "name": item.get("name")
        }
        for raw_key, val in item.items():
            if raw_key in ("id", "name"):
                continue
            friendly_key = schema.get(raw_key, raw_key)
            mapped[friendly_key] = val
        mapped_items.append(mapped)
    return mapped_items
