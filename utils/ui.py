import json
from pathlib import Path

import streamlit as st

from utils.supabase_db import SupabaseSpreadsheetAdapter

CONFIG_FILE = Path(__file__).resolve().parent.parent / ".streamlit" / "crm_config.json"


def save_sheet_id(sheet_id: str):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump({"sheet_id": sheet_id}, f)


def load_sheet_id() -> str:
    try:
        if "SHEET_ID" in st.secrets:
            return st.secrets["SHEET_ID"]
    except:
        pass
    # Fall back to local config
    config_path = Path(__file__).resolve().parent.parent / ".streamlit" / "crm_config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f).get("sheet_id", "")
        except Exception:
            return ""
    return ""


def inject_global_css():
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #050A18 0%, #0D1B3E 100%) !important;
    }
    h1 { border-left: 4px solid #C9A84C; padding-left: 12px; color: #E8ECF4; }
    h2 { border-left: 3px solid #C9A84C; padding-left: 10px; }
    .stButton > button { border-radius: 8px; font-weight: 600; }
    [data-testid="stExpander"] { border: 1px solid #1E2D4E; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)


def init_page(title):
    try:
        st.set_page_config(page_title=title, page_icon="⚙️", layout="wide")
    except:
        pass

    if "username" not in st.session_state or not st.session_state.get("username"):
        st.warning("Please login first.")
        st.stop()

    inject_global_css()


def check_admin_access():
    import streamlit as st
    # Hard override for master account
    if str(st.session_state.get("username", "")) == "7637956":
        return True

    role = str(st.session_state.get("role", "")).strip().lower()
    return role == "admin" or st.session_state.get("is_admin") is True


def admin_login_widget():
    if not st.session_state.get("is_admin", False):
        with st.expander("🔐 Admin Login — Required for Edit/Delete"):
            pwd = st.text_input("Admin Password", type="password", key="admin_pwd_input")
            if st.button("Login as Admin"):
                if pwd == "National@1975":
                    st.session_state["is_admin"] = True
                    st.success("Admin access granted!")
                    st.rerun()
                else:
                    st.error("Incorrect password.")
    else:
        st.sidebar.success("🔐 Admin logged in")
        if st.sidebar.button("Logout Admin"):
            st.session_state["is_admin"] = False
            st.rerun()


def get_spreadsheet_connection():
    existing_spreadsheet = st.session_state.get("spreadsheet_obj")
    if existing_spreadsheet is not None:
        return existing_spreadsheet

    adapter = SupabaseSpreadsheetAdapter()
    st.session_state["spreadsheet_obj"] = adapter
    return adapter
