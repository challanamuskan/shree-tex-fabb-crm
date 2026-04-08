import hashlib
import streamlit as st
from utils.supabase_db import (
    add_user as supabase_add_user,
    delete_user as supabase_delete_user,
    get_all_users as supabase_get_all_users,
    get_user,
    update_user_password,
)

ADMIN_ROLE = "admin"
EMPLOYEE_ROLE = "employee"


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_login(username: str, password: str):
    """Verify login credentials and return user info if valid."""
    try:
        row = get_user(username)
        if row and row.get("password_hash") == hash_password(password):
            must_change = row.get("must_change_password", False)
            if isinstance(must_change, str):
                must_change = must_change.strip().lower() in {"true", "1", "yes", "on"}
            return {
                "username": username,
                "role": row.get("role", ""),
                "full_name": row.get("full_name", ""),
                "email": row.get("email", ""),
                "must_change": bool(must_change),
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
    """Update a user's password hash in Supabase."""
    try:
        update_user_password(username, new_password_hash)
        return True
    except Exception as e:
        st.error(f"Error updating password: {e}")
        return False


def get_all_users():
    """Get all users from Supabase."""
    try:
        return supabase_get_all_users()
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []


def add_user(username: str, password_hash: str, role: str, full_name: str, email: str):
    """Add a new user to Supabase."""
    try:
        supabase_add_user({
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "full_name": full_name,
            "email": email,
            "must_change_password": False,
        })
        return True
    except Exception as e:
        st.error(f"Error adding user: {e}")
        return False


def remove_user(username: str):
    """Remove a user from Supabase."""
    try:
        supabase_delete_user(username)
        return True
    except Exception as e:
        st.error(f"Error removing user: {e}")
        return False


def verify_default_admin_exists():
    row = get_user("7637956")
    if row is None:
        supabase_add_user({
            "username": "7637956",
            "password_hash": hash_password(st.secrets.get("DEFAULT_ADMIN_PASSWORD", "changeme123")),
            "role": "admin",
            "full_name": "Admin",
            "email": "",
            "must_change_password": False,
        })


verify_default_admin_exists()
