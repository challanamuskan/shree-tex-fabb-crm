import streamlit as st
import pandas as pd
from utils.auth import (
    require_login,
    is_admin,
    require_admin,
    get_all_users,
    add_user,
    hash_password,
    remove_user,
    update_password_hash,
)

if "username" not in st.session_state or not st.session_state.get("username"):
    st.warning("Please login first.")
    st.stop()

require_login()
require_admin()

st.markdown("# 👥 User Management")
st.markdown("---")

# ── Current Users ─────────────────────────────────────────────────────────────
st.subheader("👥 Current Users")
users = get_all_users()
if users:
    display_users = []
    for user in users:
        # Supabase returns snake_case — handle both just in case
        created = str(user.get("created_at") or user.get("Created_At") or "")
        display_users.append({
            "Username":   user.get("username")   or user.get("Username", ""),
            "Full Name":  user.get("full_name")  or user.get("Full_Name", ""),
            "Email":      user.get("email")      or user.get("Email", ""),
            "Role":       (user.get("role") or user.get("Role", "")).capitalize(),
            "Created At": created[:10] if created else "",
        })
    st.dataframe(pd.DataFrame(display_users), use_container_width=True, hide_index=True)
else:
    st.info("No users found.")

st.markdown("---")

# ── Add New Employee ──────────────────────────────────────────────────────────
st.subheader("➕ Add New Employee")
with st.form("add_employee_form"):
    full_name  = st.text_input("Full Name", placeholder="John Doe")
    username   = st.text_input("Username / Employee ID")
    password   = st.text_input("Temporary Password", type="password")
    role       = st.selectbox("Role", options=["employee", "admin"], format_func=str.capitalize)
    email      = st.text_input("Email Address")

    if st.form_submit_button("Create Account", use_container_width=True):
        if not all([full_name.strip(), username.strip(), password.strip(), email.strip()]):
            st.error("All fields are required.")
        elif len(password) < 8:
            st.error("Password must be at least 8 characters.")
        else:
            existing = get_all_users()
            existing_usernames = {u.get("username") or u.get("Username", "") for u in (existing or [])}
            if username.strip() in existing_usernames:
                st.error(f"Username '{username.strip()}' already exists.")
            else:
                try:
                    add_user({
                        "username": username.strip(),
                        "password_hash": hash_password(password),
                        "role": role,
                        "full_name": full_name.strip(),
                        "email": email.strip(),
                        "must_change_password": "true",
                    })
                    st.success(f"✅ Account created for {full_name.strip()}. They must change their password on first login.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating account: {e}")

st.markdown("---")

# ── Reset Password ────────────────────────────────────────────────────────────
st.subheader("🔑 Reset User Password")
all_users = get_all_users() or []
user_options = [u.get("username") or u.get("Username", "") for u in all_users]
user_options = [u for u in user_options if u]

if not user_options:
    st.info("No users available.")
else:
    with st.form("reset_password_form"):
        target_user = st.selectbox("Select User", options=user_options)
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if st.form_submit_button("Reset Password", use_container_width=True):
            if not new_password.strip():
                st.error("Password cannot be empty.")
            elif len(new_password) < 8:
                st.error("Password must be at least 8 characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    update_password_hash(target_user, hash_password(new_password))
                    st.success(f"✅ Password reset for {target_user}.")
                except Exception as e:
                    st.error(f"Error resetting password: {e}")

st.markdown("---")

# ── Delete User ───────────────────────────────────────────────────────────────
st.subheader("🗑️ Remove User")
current_user = st.session_state.get("username", "")
deletable = [u for u in user_options if u != current_user]

if not deletable:
    st.info("No other users to remove.")
else:
    with st.form("delete_user_form"):
        del_user = st.selectbox("Select User to Remove", options=deletable)
        confirm = st.checkbox("I confirm I want to permanently delete this user")

        if st.form_submit_button("Delete User", use_container_width=True):
            if not confirm:
                st.error("Please confirm deletion.")
            else:
                try:
                    remove_user(del_user)
                    st.success(f"✅ User '{del_user}' removed.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error removing user: {e}")
