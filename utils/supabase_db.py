import os
import re
import time

import streamlit as st
from supabase import Client, create_client

from utils.constants import (
    ATTENDANCE_HEADERS,
    ATTENDANCE_TAB,
    CATEGORIES_HEADERS,
    CATEGORIES_TAB,
    CONTACTS_HEADERS,
    CONTACTS_TAB,
    DAILY_REPORTS_HEADERS,
    DAILY_REPORTS_TAB,
    EMAIL_LOG_HEADERS,
    EMAIL_LOG_TAB,
    EMPLOYEES_HEADERS,
    EMPLOYEES_TAB,
    EMPLOYEE_TASKS_HEADERS,
    EMPLOYEE_TASKS_TAB,
    PARTS_HEADERS,
    PARTS_TAB,
    PAYMENTS_HEADERS,
    PAYMENTS_TAB,
    PRICE_HISTORY_HEADERS,
    PRICE_HISTORY_TAB,
    PURCHASE_ORDERS_HEADERS,
    PURCHASE_ORDERS_TAB,
    PURCHASE_RECORDS_HEADERS,
    PURCHASE_RECORDS_TAB,
    RETURNS_HEADERS,
    RETURNS_TAB,
    SALES_RECORDS_HEADERS,
    SALES_RECORDS_TAB,
    SETTINGS_HEADERS,
    SETTINGS_TAB,
)


TABLE_HEADERS = {
    PARTS_TAB: PARTS_HEADERS,
    CATEGORIES_TAB: CATEGORIES_HEADERS,
    PRICE_HISTORY_TAB: PRICE_HISTORY_HEADERS,
    CONTACTS_TAB: CONTACTS_HEADERS,
    PAYMENTS_TAB: PAYMENTS_HEADERS,
    PURCHASE_ORDERS_TAB: PURCHASE_ORDERS_HEADERS,
    SALES_RECORDS_TAB: SALES_RECORDS_HEADERS,
    PURCHASE_RECORDS_TAB: PURCHASE_RECORDS_HEADERS,
    RETURNS_TAB: RETURNS_HEADERS,
    EMAIL_LOG_TAB: EMAIL_LOG_HEADERS,
    EMPLOYEES_TAB: EMPLOYEES_HEADERS,
    EMPLOYEE_TASKS_TAB: EMPLOYEE_TASKS_HEADERS,
    DAILY_REPORTS_TAB: DAILY_REPORTS_HEADERS,
    ATTENDANCE_TAB: ATTENDANCE_HEADERS,
    SETTINGS_TAB: SETTINGS_HEADERS,
}

TABLE_ALIASES = {
    "parts": "parts",
    PARTS_TAB.lower(): "parts",
    "categories": "categories",
    CATEGORIES_TAB.lower(): "categories",
    "price_history": "price_history",
    PRICE_HISTORY_TAB.lower(): "price_history",
    "customers": "customers",
    "customers_leads": "customers",
    CONTACTS_TAB.lower(): "customers",
    "payments": "payments",
    PAYMENTS_TAB.lower(): "payments",
    "purchase_orders": "purchase_orders",
    PURCHASE_ORDERS_TAB.lower(): "purchase_orders",
    "sales_records": "sales_records",
    SALES_RECORDS_TAB.lower(): "sales_records",
    "purchase_records": "purchase_records",
    PURCHASE_RECORDS_TAB.lower(): "purchase_records",
    "returns": "returns",
    RETURNS_TAB.lower(): "returns",
    "email_log": "email_log",
    EMAIL_LOG_TAB.lower(): "email_log",
    "employees": "employees",
    EMPLOYEES_TAB.lower(): "employees",
    "employee_tasks": "employee_tasks",
    EMPLOYEE_TASKS_TAB.lower(): "employee_tasks",
    "daily_reports": "daily_reports",
    DAILY_REPORTS_TAB.lower(): "daily_reports",
    "attendance": "attendance",
    ATTENDANCE_TAB.lower(): "attendance",
    "settings": "settings",
    SETTINGS_TAB.lower(): "settings",
}


def _normalize_key(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _resolve_table_name(table_name):
    if hasattr(table_name, "table_name"):
        table_name = getattr(table_name, "table_name")
    elif hasattr(table_name, "title") and not isinstance(table_name, str):
        table_name = getattr(table_name, "title")
    lookup = _normalize_key(table_name)
    return TABLE_ALIASES.get(lookup, lookup)


def _headers_for_table(table_name):
    if hasattr(table_name, "headers") and getattr(table_name, "headers"):
        return list(getattr(table_name, "headers"))
    if hasattr(table_name, "title") and getattr(table_name, "title") in TABLE_HEADERS:
        return TABLE_HEADERS[getattr(table_name, "title")]
    return TABLE_HEADERS.get(table_name) or TABLE_HEADERS.get(table_name.title()) or []


def _clean_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return None if stripped == "" else stripped
    return value


def _display_key_from_db_key(key):
    parts = str(key).split("_")
    return "_".join(part.capitalize() if part else part for part in parts)


def _row_to_payload(row, headers=None):
    if headers:
        payload = {}
        for header in headers:
            payload[_normalize_key(header)] = row.get(_normalize_key(header), row.get(header, ""))
        return payload
    return {k: v for k, v in row.items() if k != "id"}


def _fetch_raw_rows(table_name):
    try:
        sb = get_supabase()
        response = sb.table(_resolve_table_name(table_name)).select("*").limit(10000).execute()
        return response.data if response.data else []
    except Exception as exc:
        st.error(f"Database error fetching {table_name}: {exc}")
        return []


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise KeyError("SUPABASE_URL and SUPABASE_KEY must be set in Streamlit secrets or environment variables")
    return create_client(str(url), str(key))


@st.cache_data(ttl=1, show_spinner=False)
def fetch_table(table_name):
    return _fetch_raw_rows(table_name)


def insert_record(table_name, record_dict):
    try:
        sb = get_supabase()
        clean = {k: _clean_value(v) for k, v in record_dict.items() if k != "_row"}
        return sb.table(_resolve_table_name(table_name)).insert(clean).execute()
    except Exception as exc:
        st.error(f"Insert error: {exc}")
        return None


def update_record(table_name, record_dict, match_column, match_value):
    try:
        sb = get_supabase()
        clean = {k: _clean_value(v) for k, v in record_dict.items() if k != "_row"}
        return sb.table(_resolve_table_name(table_name)).update(clean).eq(match_column, match_value).execute()
    except Exception as exc:
        st.error(f"Update error: {exc}")
        return None


def delete_record(table_name, match_column, match_value=None):
    try:
        sb = get_supabase()
        query = sb.table(_resolve_table_name(table_name)).delete()
        if match_value is None:
            match_value = match_column
            match_column = "id"
        return query.eq(match_column, match_value).execute()
    except Exception as exc:
        st.error(f"Delete error: {exc}")
        return None


def bulk_insert(table_name, list_of_dicts):
    try:
        sb = get_supabase()
        cleaned = []
        for record in list_of_dicts:
            clean = {
                _normalize_key(k): _clean_value(v)
                for k, v in record.items()
                if k != "_row"
            }
            cleaned.append(clean)
        for i in range(0, len(cleaned), 500):
            chunk = cleaned[i : i + 500]
            sb.table(_resolve_table_name(table_name)).insert(chunk).execute()
            time.sleep(0.5)
        return True, len(cleaned)
    except Exception as exc:
        return False, str(exc)


def _rows_with_legacy_keys(table_name):
    headers = _headers_for_table(table_name)
    rows = []
    for idx, record in enumerate(_fetch_raw_rows(table_name), start=1):
        if headers:
            row = {}
            for header in headers:
                key = _normalize_key(header)
                row[header] = record.get(key, record.get(header, ""))
        else:
            row = dict(record)
        for key, value in record.items():
            display_key = _display_key_from_db_key(key)
            row.setdefault(display_key, value)
        row["_row"] = record.get("id", idx)
        rows.append(row)
    return rows


def fetch_tab(table_name):
    return _rows_with_legacy_keys(table_name)


def fetch_sheet_data_by_name(table_name, headers=None):
    headers = headers or _headers_for_table(table_name)
    rows = []
    for record in _fetch_raw_rows(table_name):
        row = {}
        for header in headers:
            key = _normalize_key(header)
            row[header] = record.get(key, record.get(header, ""))
        for key, value in record.items():
            row.setdefault(_display_key_from_db_key(key), value)
        row["_row"] = record.get("id")
        rows.append(row)
    return rows


class SupabaseWorksheet:
    def __init__(self, table_name, headers=None):
        self.table_name = _resolve_table_name(table_name)
        self.title = table_name
        self.headers = headers or _headers_for_table(table_name)

    def _payload_from_row(self, values):
        if isinstance(values, dict):
            return values
        return {header: values[idx] if idx < len(values) else "" for idx, header in enumerate(self.headers)}

    def append_row(self, values, value_input_option=None):
        return insert_record(self.table_name, self._payload_from_row(values))

    def append_rows(self, rows, value_input_option=None):
        for row in rows:
            self.append_row(row, value_input_option=value_input_option)
        return True

    def update(self, cell_range, values, value_input_option=None):
        match = re.search(r"(\d+)", str(cell_range))
        if not match:
            return None
        row_number = int(match.group(1))
        payload = self._payload_from_row(values[0] if values and isinstance(values[0], list) else values)
        return update_record(self.table_name, payload, "id", row_number)

    def delete_rows(self, row_number):
        return delete_record(self.table_name, "id", row_number)

    def col_values(self, column_index):
        headers = self.headers or []
        if column_index < 1:
            return []
        if not headers:
            return []
        header = headers[column_index - 1] if column_index - 1 < len(headers) else headers[0]
        values = [header]
        for row in _fetch_raw_rows(self.table_name):
            values.append(str(row.get(_normalize_key(header), row.get(header, "")) or ""))
        return values

    def row_values(self, row_number):
        rows = fetch_sheet_data_by_name(self.title, self.headers)
        if row_number == 1:
            return list(self.headers)
        for row in rows:
            if row.get("_row") == row_number:
                return [row.get(header, "") for header in self.headers]
        return []


class SupabaseSpreadsheetAdapter:
    def worksheet(self, tab_name):
        return SupabaseWorksheet(tab_name)

    def worksheets(self):
        return [SupabaseWorksheet(tab_name, headers) for tab_name, headers in TABLE_HEADERS.items()]

    def add_worksheet(self, title, rows=1000, cols=10):
        return SupabaseWorksheet(title)


def get_or_create_worksheet(_spreadsheet, tab_name, headers=None):
    return SupabaseWorksheet(tab_name, headers)


def append_record(table_name, _headers, record_dict):
    return insert_record(table_name, record_dict)


def bulk_append_records(table_name, _headers, records):
    return bulk_insert(table_name, records)


def update_part_quantity(part_name: str, delta: int):
    sb = get_supabase()
    parts = sb.table("parts").select("id,quantity").eq("part_name", part_name).execute().data
    if parts:
        current_qty = parts[0].get("quantity") or 0
        try:
            current_qty = int(float(str(current_qty).strip()))
        except (TypeError, ValueError):
            current_qty = 0
        new_qty = max(0, current_qty + delta)
        sb.table("parts").update({"quantity": new_qty}).eq("id", parts[0]["id"]).execute()


def update_part_image(part_id: str, image_base64: str):
    sb = get_supabase()
    return sb.table("parts").update({"image": image_base64}).eq("id", part_id).execute()


def get_parts():
    return fetch_table("parts")


def add_part(data: dict):
    return insert_record("parts", data)


def update_part(part_id: str, data: dict):
    return update_record("parts", data, "id", part_id)


def delete_part(part_id: str):
    return delete_record("parts", "id", part_id)


def get_categories():
    return fetch_table("categories")


def add_category(data: dict):
    return insert_record("categories", data)


def get_customers():
    return fetch_table("customers")


def add_customer(data: dict):
    return insert_record("customers", data)


def update_customer(cid: str, data: dict):
    return update_record("customers", data, "id", cid)


def delete_customer(cid: str):
    return delete_record("customers", "id", cid)


def get_payments():
    return fetch_table("payments")


def add_payment(data: dict):
    return insert_record("payments", data)


def update_payment(pid: str, data: dict):
    return update_record("payments", data, "id", pid)


def delete_payment(pid: str):
    return delete_record("payments", "id", pid)


def get_purchase_orders():
    return fetch_table("purchase_orders")


def add_purchase_order(data: dict):
    return insert_record("purchase_orders", data)


def update_purchase_order(oid: str, data: dict):
    return update_record("purchase_orders", data, "id", oid)


def delete_purchase_order(oid: str):
    return delete_record("purchase_orders", "id", oid)


def get_sales_records():
    return fetch_table("sales_records")


def add_sale(data: dict):
    return insert_record("sales_records", data)


def get_purchase_records():
    return fetch_table("purchase_records")


def add_purchase_record(data: dict):
    return insert_record("purchase_records", data)


def get_returns():
    return fetch_table("returns")


def add_return(data: dict):
    return insert_record("returns", data)


def get_employees():
    return fetch_table("employees")


def add_employee(data: dict):
    return insert_record("employees", data)


def delete_employee(eid: str):
    return delete_record("employees", "id", eid)


def get_tasks(date_str: str = None):
    sb = get_supabase()
    q = sb.table("employee_tasks").select("*")
    if date_str:
        q = q.eq("date", date_str)
    return q.execute().data


def add_task(data: dict):
    return insert_record("employee_tasks", data)


def get_daily_reports(date_str: str = None):
    sb = get_supabase()
    q = sb.table("daily_reports").select("*")
    if date_str:
        q = q.eq("date", date_str)
    return q.execute().data


def add_daily_report(data: dict):
    return insert_record("daily_reports", data)


def get_attendance(date_str: str = None):
    sb = get_supabase()
    q = sb.table("attendance").select("*")
    if date_str:
        q = q.eq("date", date_str)
    return q.execute().data


def upsert_attendance(data: dict):
    sb = get_supabase()
    return sb.table("attendance").upsert(data, on_conflict="date,employee_name").execute()


def get_email_log():
    sb = get_supabase()
    return sb.table("email_log").select("*").order("timestamp", desc=True).limit(50).execute().data


def add_email_log(data: dict):
    return insert_record("email_log", data)


def get_user(username: str):
    sb = get_supabase()
    result = sb.table("users").select("*").eq("username", username).execute().data
    return result[0] if result else None


def add_user(data: dict):
    return insert_record("users", data)


def update_user_password(username: str, new_hash: str):
    sb = get_supabase()
    return sb.table("users").update({"password_hash": new_hash, "must_change_password": False}).eq("username", username).execute()


def delete_user(username: str):
    sb = get_supabase()
    return sb.table("users").delete().eq("username", username).execute()


def get_all_users():
    sb = get_supabase()
    return sb.table("users").select("username,role,full_name,email,created_at").execute().data


def get_price_history(part_name: str = None):
    sb = get_supabase()
    q = sb.table("price_history").select("*")
    if part_name:
        q = q.eq("part_name", part_name)
    return q.execute().data


def add_price_history(data: dict):
    return insert_record("price_history", data)


def get_dashboard_stats():
    parts = fetch_table("parts")
    payments = fetch_table("payments")
    contacts = fetch_table("customers")
    low_stock = 0
    for row in parts:
        try:
            qty = int(float(str(row.get("quantity", 0)).strip() or 0))
        except (TypeError, ValueError):
            qty = 0
        try:
            reorder = int(float(str(row.get("reorder_level", 0)).strip() or 0))
        except (TypeError, ValueError):
            reorder = 0
        if reorder > 0 and qty <= reorder:
            low_stock += 1
    pending_total = 0.0
    for row in payments:
        if str(row.get("status", "")).strip().lower() != "paid":
            try:
                pending_total += float(str(row.get("amount", 0)).strip() or 0)
            except (TypeError, ValueError):
                continue
    open_leads = sum(1 for row in contacts if str(row.get("lead_status", "")).strip().lower() in {"new", "contacted", "interested", "negotiation"})
    return {
        "total_parts": len(parts),
        "low_stock": low_stock,
        "pending_payments": pending_total,
        "open_leads": open_leads,
    }


# Backward-compatible aliases still used throughout the app during migration.
def fetch_sheet_data_by_name_compat(table_name, headers=None):
    return fetch_sheet_data_by_name(table_name, headers)
