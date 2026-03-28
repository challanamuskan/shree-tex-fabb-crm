import json
from pathlib import Path

import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

CONFIG_FILE = Path(__file__).resolve().parent.parent / ".streamlit" / "crm_config.json"


def get_credentials():
    import streamlit as st
    from oauth2client.service_account import ServiceAccountCredentials
    import json, tempfile, os
    from pathlib import Path

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # Try Streamlit secrets first (cloud deployment)
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds_dict["type"] = "service_account"
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
            json.dump(creds_dict, tmp)
            tmp.flush()
            return ServiceAccountCredentials.from_json_keyfile_name(tmp.name, scope)
    except Exception:
        pass

    # Fall back to local file
    creds_path = Path(__file__).resolve().parent.parent / "textile-part-crm-24280a22d7d9.json"
    return ServiceAccountCredentials.from_json_keyfile_name(str(creds_path), scope)


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
    inject_global_css()


def check_admin_access():
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False
    return st.session_state["is_admin"]


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
    saved_id = load_sheet_id()
    with st.sidebar:
        st.markdown("---")
        sheet_id = st.text_input("Google Sheet ID", value=saved_id, key="sheet_id_input")
        if st.button("Connect") or saved_id:
            if sheet_id:
                try:
                    creds = get_credentials()
                    client = gspread.authorize(creds)
                    spreadsheet = client.open_by_key(sheet_id)
                    save_sheet_id(sheet_id)
                    st.sidebar.success("✅ Connected")
                    return spreadsheet
                except Exception as e:
                    st.sidebar.error(f"Connection failed: {e}")
                    return None
    return None
