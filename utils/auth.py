import hashlib
import secrets
import datetime
import json
from pathlib import Path

import gspread
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

ADMIN_ROLE = "admin"
EMPLOYEE_ROLE = "employee"


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


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def load_sheet_id():
    """Load the Google Sheet ID from crm_config.json"""
    config_path = Path(__file__).resolve().parent.parent / ".streamlit" / "crm_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f).get("sheet_id", "")
    return ""


def get_users_sheet():
    """Get or create the Users sheet in Google Sheets."""
    creds = get_credentials()
    client = gspread.authorize(creds)
    sheet_id = load_sheet_id()
    if not sheet_id:
        st.error("Sheet ID not found in crm_config.json")
        st.stop()
    spreadsheet = client.open_by_key(sheet_id)

    try:
        return spreadsheet.worksheet("Users")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet("Users", 100, 10)
        ws.append_row([
            "Username",
            "Password_Hash",
            "Role",
            "Full_Name",
            "Email",
            "Must_Change_Password",
            "Created_At",
        ])
        # Create default admin account
        ws.append_row([
            "7637956",
            hash_password("dywoftuvrm@Z"),
            "admin",
            "Admin",
            "",
            "False",
            str(datetime.datetime.now()),
        ])
        return ws


def verify_login(username: str, password: str):
    """Verify login credentials and return user info if valid."""
    try:
        ws = get_users_sheet()
        records = ws.get_all_records()
        for row in records:
            if str(row["Username"]).strip() == str(username).strip() and row["Password_Hash"] == hash_password(
                password
            ):
                return {
                    "username": username,
                    "role": row["Role"],
                    "full_name": row["Full_Name"],
                    "email": row["Email"],
                    "must_change": str(row["Must_Change_Password"]).lower() == "true",
                }
        return None
    except Exception as e:
        st.error(f"Login error: {e}")
        return None


def is_logged_in():
    """Check if user is logged in."""
    return st.session_state.get("logged_in", False)


def is_admin():
    """Check if logged in user is an admin."""
    return st.session_state.get("user_role") == ADMIN_ROLE


def require_login():
    """Require user to be logged in, stop page if not."""
    if not is_logged_in():
        st.error("Please log in to access this page.")
        st.stop()


def require_admin():
    """Require user to be an admin, stop page if not."""
    if not is_admin():
        st.warning("🔐 Admin access required for this section.")
        st.stop()


def logout():
    """Clear login session state."""
    for key in ["logged_in", "username", "user_role", "user_fullname", "user_email"]:
        st.session_state.pop(key, None)


def update_password_hash(username: str, new_password_hash: str):
    """Update a user's password hash in the Users sheet."""
    try:
        ws = get_users_sheet()
        records = ws.get_all_records()
        for idx, row in enumerate(records, start=2):  # Start at 2 because row 1 is header
            if str(row["Username"]).strip() == str(username).strip():
                ws.update_cell(idx, 2, new_password_hash)  # Column 2 is Password_Hash
                return True
        return False
    except Exception as e:
        st.error(f"Error updating password: {e}")
        return False


def get_all_users():
    """Get all users from the Users sheet."""
    try:
        ws = get_users_sheet()
        records = ws.get_all_records()
        return records
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []


def add_user(username: str, password_hash: str, role: str, full_name: str, email: str):
    """Add a new user to the Users sheet."""
    try:
        ws = get_users_sheet()
        ws.append_row([
            username,
            password_hash,
            role,
            full_name,
            email,
            "False",
            str(datetime.datetime.now()),
        ])
        return True
    except Exception as e:
        st.error(f"Error adding user: {e}")
        return False


def remove_user(username: str):
    """Remove a user from the Users sheet."""
    try:
        ws = get_users_sheet()
        records = ws.get_all_records()
        for idx, row in enumerate(records, start=2):
            if str(row["Username"]).strip() == str(username).strip():
                ws.delete_rows(idx)
                return True
        return False
    except Exception as e:
        st.error(f"Error removing user: {e}")
        return False
