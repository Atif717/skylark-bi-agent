import requests
import logging
import time
import json
import os

logger = logging.getLogger(__name__)

class MondayClient:
    """
    A thin, native GraphQL client for Monday.com.
    Includes robust retries for rate limits or connection glitches, 
    and a local excel-backed mock converter for offline demo runs.
    """
    API_URL = "https://api.monday.com/v2"

    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": self.api_token or "",
            "Content-Type": "application/json",
            "API-Version": "2024-01"
        }

    def execute_query(self, query: str, variables: dict = None) -> dict:
        """
        Executes a GraphQL query/mutation, retrying once on transient failure (rate limits or 5xx).
        """
        # If API token is placeholder/mock, use local Excel converter
        if not self.api_token or "mock" in self.api_token.lower() or self.api_token == "xyz_placeholder":
            return self._get_excel_mock_response(query, variables)

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        # Attempt query execution (up to 2 tries: 1 original + 1 retry)
        for attempt in range(2):
            try:
                response = requests.post(self.API_URL, json=payload, headers=self.headers, timeout=10)
                
                # If rate limit (429) or server error (5xx), raise to trigger retry
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    response.raise_for_status()
                
                response.raise_for_status()
                
                data = response.json()
                if "errors" in data:
                    logger.error(f"Monday.com GraphQL error: {data['errors']}")
                    raise ValueError(f"GraphQL Error: {data['errors'][0]['message']}")
                    
                return data
                
            except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
                if attempt == 0:
                    logger.warning(f"Transient error: {e}. Retrying execution once in 1 second...")
                    time.sleep(1.0)
                    continue
                else:
                    logger.error(f"Permanent connection error on Monday.com client: {e}")
                    raise RuntimeError(f"Monday.com Connection Error: {e}")

    def _get_excel_mock_response(self, query: str, variables: dict = None) -> dict:
        """
        Interprets Monday board queries, reads raw Excel sheets, and transforms
        them into Monday GraphQL JSON structures with pagination cursor support.
        """
        import pandas as pd
        
        board_id = variables.get("board_id") if variables else None
        
        is_deals = False
        is_work_orders = False
        
        if board_id:
            board_id_str = str(board_id)
            if "5030967387" in board_id_str:
                is_deals = True
            elif "5030967210" in board_id_str:
                is_work_orders = True
        
        # Fallback check
        if not (is_deals or is_work_orders):
            if "deal" in query.lower():
                is_deals = True
            else:
                is_work_orders = True

        all_items = []
        board_name = ""
        actual_board_id = ""

        if is_deals:
            board_name = "Deals Board"
            actual_board_id = "5030967387"
            file_path = "Deal_funnel_Data.xlsx"
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Missing sample file {file_path}. Please copy it to workspace.")
                
            df = pd.read_excel(file_path)
            for idx, row in df.iterrows():
                # Extract main name
                name_val = row.get("Deal Name")
                name = str(name_val).strip() if not pd.isna(name_val) else f"Deal {idx}"
                
                column_values = []
                for excel_col, raw_id in [
                    ('Owner code', 'owner_code'),
                    ('Client Code', 'client_code'),
                    ('Deal Status', 'deal_status'),
                    ('Close Date (A)', 'close_date_a'),
                    ('Closure Probability', 'closure_probability'),
                    ('Masked Deal value', 'masked_deal_value'),
                    ('Tentative Close Date', 'tentative_close_date'),
                    ('Deal Stage', 'deal_stage'),
                    ('Product deal', 'product_deal'),
                    ('Sector/service', 'sector_service'),
                    ('Created Date', 'created_date')
                ]:
                    val = row.get(excel_col)
                    val_str = ""
                    if not pd.isna(val):
                        if isinstance(val, pd.Timestamp):
                            val_str = val.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            val_str = str(val)
                    
                    column_values.append({
                        "id": raw_id,
                        "text": val_str,
                        "value": json.dumps({"value": val_str}) if val_str else None
                    })
                all_items.append({
                    "id": f"deal_{idx}",
                    "name": name,
                    "column_values": column_values
                })
        else:
            board_name = "Work Orders Board"
            actual_board_id = "5030967210"
            file_path = "Work_Order_Tracker_Data.xlsx"
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Missing sample file {file_path}. Please copy it to workspace.")
                
            df = pd.read_excel(file_path, header=1)
            for idx, row in df.iterrows():
                # Serial # as key identifier
                serial_val = row.get("Serial #")
                serial_no = str(serial_val).strip() if not pd.isna(serial_val) else f"WO_{idx}"
                
                column_values = []
                for excel_col, raw_id in [
                    ('Deal name masked', 'deal_name_masked'),
                    ('Customer Name Code', 'customer_name_code'),
                    ('Nature of Work', 'nature_of_work'),
                    ('Last executed month of recurring project', 'last_executed_month'),
                    ('Execution Status', 'execution_status'),
                    ('Data Delivery Date', 'data_delivery_date'),
                    ('Date of PO/LOI', 'date_of_po'),
                    ('Document Type', 'document_type'),
                    ('Probable Start Date', 'probable_start_date'),
                    ('Probable End Date', 'probable_end_date'),
                    ('BD/KAM Personnel code', 'bd_kam_code'),
                    ('Sector', 'sector'),
                    ('Type of Work', 'type_of_work'),
                    ('Is any Skylark software platform part of the client deliverables in this deal?', 'skylark_software_part'),
                    ('Last invoice date', 'last_invoice_date'),
                    ('latest invoice no.', 'latest_invoice_no'),
                    ('Amount in Rupees (Excl of GST) (Masked)', 'amount_excl_gst'),
                    ('Amount in Rupees (Incl of GST) (Masked)', 'amount_incl_gst'),
                    ('Billed Value in Rupees (Excl of GST.) (Masked)', 'billed_excl_gst'),
                    ('Billed Value in Rupees (Incl of GST.) (Masked)', 'billed_incl_gst'),
                    ('Collected Amount in Rupees (Incl of GST.) (Masked)', 'collected_incl_gst'),
                    ('Amount to be billed in Rs. (Exl. of GST) (Masked)', 'to_be_billed_excl_gst'),
                    ('Amount to be billed in Rs. (Incl. of GST) (Masked)', 'to_be_billed_incl_gst'),
                    ('Amount Receivable (Masked)', 'amount_receivable'),
                    ('AR Priority account', 'ar_priority_account'),
                    ('Quantity by Ops', 'quantity_by_ops'),
                    ('Quantities as per PO', 'quantities_per_po'),
                    ('Quantity billed (till date)', 'quantity_billed'),
                    ('Balance in quantity', 'balance_quantity'),
                    ('Invoice Status', 'invoice_status'),
                    ('Expected Billing Month', 'expected_billing_month'),
                    ('Actual Billing Month', 'actual_billing_month'),
                    ('Actual Collection Month', 'actual_collection_month'),
                    ('WO Status (billed)', 'wo_status_billed'),
                    ('Collection status', 'collection_status'),
                    ('Collection Date', 'collection_date'),
                    ('Billing Status', 'billing_status')
                ]:
                    val = row.get(excel_col)
                    val_str = ""
                    if not pd.isna(val):
                        if isinstance(val, pd.Timestamp):
                            val_str = val.strftime("%Y-%m-%d %H:%M:%S")
                        else:
                            val_str = str(val)
                    
                    column_values.append({
                        "id": raw_id,
                        "text": val_str,
                        "value": json.dumps({"value": val_str}) if val_str else None
                    })
                all_items.append({
                    "id": f"wo_{idx}",
                    "name": serial_no,
                    "column_values": column_values
                })

        # Emulate Cursor Pagination (Chunking by 50 rows per page)
        limit = 50
        start = 0
        cursor = variables.get("cursor") if variables else None
        
        if cursor:
            try:
                start = int(cursor.split("_")[-1])
            except ValueError:
                start = 0
                
        end = start + limit
        items_slice = all_items[start:end]
        next_cursor = f"cursor_{end}" if end < len(all_items) else None

        return {
            "data": {
                "boards": [{
                    "id": actual_board_id,
                    "name": board_name,
                    "items_page": {
                        "cursor": next_cursor,
                        "items": items_slice
                    }
                }]
            }
        }
