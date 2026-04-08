from supabase import create_client
import streamlit as st
import time


@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_table(table_name):
    try:
        sb = get_supabase()
        response = sb.table(table_name).select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Database error fetching {table_name}: {e}")
        return []


def insert_record(table_name, record_dict):
    try:
        sb = get_supabase()
        # Clean the dict -- remove empty strings for non-text fields
        clean = {k: (v if v != "" else None) for k, v in record_dict.items()}
        return sb.table(table_name).insert(clean).execute()
    except Exception as e:
        st.error(f"Insert error: {e}")
        return None


def update_record(table_name, record_dict, match_column, match_value):
    try:
        sb = get_supabase()
        return sb.table(table_name).update(record_dict).eq(match_column, match_value).execute()
    except Exception as e:
        st.error(f"Update error: {e}")
        return None


def delete_record(table_name, match_column, match_value):
    try:
        sb = get_supabase()
        return sb.table(table_name).delete().eq(match_column, match_value).execute()
    except Exception as e:
        st.error(f"Delete error: {e}")
        return None


def bulk_insert(table_name, list_of_dicts):
    try:
        sb = get_supabase()
        # Clean all dicts
        cleaned = []
        for record in list_of_dicts:
            clean = {
                k: (str(v) if v is not None and str(v) not in ["nan", "None", ""] else None)
                for k, v in record.items()
            }
            cleaned.append(clean)
        # Insert in chunks of 500
        for i in range(0, len(cleaned), 500):
            chunk = cleaned[i : i + 500]
            sb.table(table_name).insert(chunk).execute()
            time.sleep(0.5)
        return True, len(cleaned)
    except Exception as e:
        return False, str(e)


# Backward-compatible aliases for existing code paths still transitioning from Sheets APIs.
def fetch_tab(table_name):
    return fetch_table(table_name)


def fetch_sheet_data_by_name(table_name, _headers=None):
    return fetch_table(table_name)


def get_or_create_worksheet(_spreadsheet, table_name, _headers=None):
    return table_name


def append_record(table_name, _headers, record_dict):
    return insert_record(table_name, record_dict)


def bulk_append_records(table_name, _headers, records):
    return bulk_insert(table_name, records)
