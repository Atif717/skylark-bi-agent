"""
Schema definitions mapping Monday.com internal column IDs to clean, standardized names.
"""

DEALS_SCHEMA = {
    "item_id": "item_id",
    "name": "name",
    "status": "deal_status",
    "date4": "created_date",
    "text_mm6q25dk": "owner_code",
    "text_mm6qj093": "client_code",
    "text_mm6qp4h1": "close_date",
    "text_mm6qebe8": "closure_probability",
    "text_mm6qerm1": "deal_value",
    "text_mm6q3res": "tentative_close_date",
    "text_mm6q5hh0": "deal_stage",
    "text_mm6qtsq0": "product",
    "text_mm6q98ma": "sector",
}

WORK_ORDERS_SCHEMA = {
    "item_id": "item_id",
    "name": "name",
    "project_status": "execution_status",
    "text_mm6qteac": "customer_name_code",
    "text_mm6qtyme": "deal_name",
    "text_mm6qz1kt": "nature_of_work",
    "text_mm6qnhx7": "last_executed_month",
    "text_mm6qbk70": "data_delivery_date",
    "text_mm6qw8ze": "date_of_po",
    "text_mm6q4wr7": "document_type",
    "text_mm6qwkkz": "probable_start_date",
    "text_mm6qphfc": "probable_end_date",
    "text_mm6qyxkm": "bd_kam_code",
    "text_mm6qqkm1": "sector",
    "text_mm6qp676": "type_of_work",
    "text_mm6qbb8m": "skylark_software_part",
    "text_mm6qq748": "last_invoice_date",
    "text_mm6qwyd0": "latest_invoice_no",
    "text_mm6qv953": "amount_excl_gst",
    "text_mm6qfgj0": "amount_incl_gst",
    "text_mm6qrfj4": "billed_excl_gst",
    "text_mm6q3js8": "billed_incl_gst",
    "text_mm6qtqkd": "collected_incl_gst",
    "text_mm6q2jma": "to_be_billed_excl_gst",
    "text_mm6qk578": "to_be_billed_incl_gst",
    "text_mm6qfxy0": "amount_receivable",
    "text_mm6qwrv": "ar_priority_account",
    "text_mm6q6v9c": "quantity_by_ops",
    "text_mm6qzxhq": "quantities_per_po",
    "text_mm6qzqez": "quantity_billed",
    "text_mm6qewtf": "balance_quantity",
    "text_mm6qfdzm": "invoice_status",
    "text_mm6qc93y": "actual_billing_month",
    "text_mm6q8mr4": "collection_status",
    "text_mm6q5gzh": "billing_status",
}


def map_columns(raw_items: list, schema: dict) -> list:
    """
    Translates raw Monday.com item dictionary keys to standard schema field names.
    Handles both raw API column_values list formats and flattened dictionary representations.
    """
    mapped_items = []
    for item in raw_items:
        row = {}
        # 1. Base top-level keys
        for k in ["id", "item_id", "name"]:
            if k in item:
                target_key = schema.get(k, k)
                row[target_key] = item[k]

        # 2. Raw Monday API format: item contains 'column_values'
        if "column_values" in item and isinstance(item["column_values"], list):
            for col in item["column_values"]:
                col_id = col.get("id")
                if col_id in schema:
                    val = col.get("text")
                    if val is None or val == "":
                        val = col.get("value")
                    row[schema[col_id]] = val

        # 3. Flattened dictionary format
        for k, v in item.items():
            if k in schema:
                row[schema[k]] = v

        mapped_items.append(row)
    return mapped_items