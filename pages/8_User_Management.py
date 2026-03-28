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

require_login()
require_admin()

st.set_page_config(page_title="User Management - Satyam Tex Fabb")

st.markdown("# 👥 User Management")
st.markdown("---")

# Section 1: Current Users Table
st.subheader("👥 Current Users")
users = get_all_users()
if users:
    display_users = []
    for user in users:
        display_users.append({
            "Username": user.get("Username", ""),
            "Full Name": user.get("Full_Name", ""),
            "Email": user.get("Email", ""),
            "Role": user.get("Role", "").capitalize(),
            "Created At": user.get("Created_At", "")[:10],  # Just the date part
        })
    users_df = pd.DataFrame(display_users)
    st.dataframe(users_df, use_container_width=True, hide_index=True)
else:
    st.info("No users found.")

st.markdown("---")

# Section 2: Add New Employee
st.subheader("➕ Add New Employee")
with st.form("add_employee_form"):
    full_name = st.text_input("Full Name", placeholder="John Doe")
    username = st.text_input("Username (Employee ID)", placeholder="Enter employee ID")
    password = st.text_input("Temporary Password", type="password", placeholder="Enter a temporary password")
    role = st.selectbox("Role", options=["employee", "admin"], format_func=str.capitalize)
    email = st.text_input("Email Address", placeholder="john@example.com")

    submit_button = st.form_submit_button("Create Account", use_container_width=True)

    if submit_button:
        if not all([full_name, username, password, email]):
            st.error("All fields are required.")
        elif len(password) < 8:
            st.error("Password must be at least 8 characters long.")
        else:
            # Check if username already exists
            existing_users = get_all_users()
            username_exists = any(
                str(u.get("Username", "")) == str(username) for u in existing_users
            )
            if username_exists:
                st.error("Username already exists.")
            else:
                if add_user(
                    username,
                    hash_password(password),
                    role,
                    full_name,
                    email,
                ):
                    st.success("✅ Employee account created successfully!")
                    st.info(f"""
**Share these credentials with the employee:**

- **Username:** {username}
- **Temporary Password:** {password}
- **Role:** {role.capitalize()}

⚠️ The employee MUST change their password on first login.
""")
                    st.rerun()
                else:
                    st.error("Failed to create account.")

st.markdown("---")

# Section 3: Reset Employee Password
st.subheader("🔑 Reset Employee Password")

existing_users = get_all_users()
if existing_users:
    usernames = [u.get("Username", "") for u in existing_users]
    # Filter out the current user
    other_usernames = [u for u in usernames if u != st.session_state.get("username", "")]

    if other_usernames:
        with st.form("reset_password_form"):
            selected_username = st.selectbox("Select Employee", options=other_usernames)
            new_password = st.text_input("New Password", type="password", placeholder="Enter new temporary password")
            submit_reset = st.form_submit_button("Reset Password", use_container_width=True)

            if submit_reset:
                if not new_password:
                    st.error("Password is required.")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long.")
                else:
                    if update_password_hash(selected_username, hash_password(new_password)):
                        st.success(f"✅ Password reset for {selected_username}")
                        st.info(f"New password: {new_password}")
                    else:
                        st.error("Failed to reset password.")
    else:
        st.info("No other employees to reset.")
else:
    st.info("No employees found.")

st.markdown("---")

# Section 4: Remove Employee
st.subheader("❌ Remove Employee")

existing_users = get_all_users()
if existing_users:
    # Filter out the current user (admin cannot remove themselves)
    other_usernames = [
        u.get("Username", "") for u in existing_users
        if u.get("Username", "") != st.session_state.get("username", "")
    ]

    if other_usernames:
        col1, col2 = st.columns([2, 1])
        with col1:
            remove_username = st.selectbox(
                "Select Employee to Remove",
                options=other_usernames,
                key="remove_user_select",
            )
        with col2:
            st.write("")
            st.write("")
            if st.button("Remove Account", use_container_width=True, type="secondary"):
                with st.form("confirm_remove_form"):
                    st.warning(f"⚠️ Are you sure you want to remove **{remove_username}**?")
                    st.caption("This action cannot be undone.")
                    confirm_checkbox = st.checkbox("I confirm removal of this account")
                    confirm_button = st.form_submit_button("Confirm Removal", use_container_width=True)

                    if confirm_button:
                        if confirm_checkbox:
                            if remove_user(remove_username):
                                st.success(f"✅ Employee {remove_username} has been removed.")
                                st.rerun()
                            else:
                                st.error("Failed to remove employee.")
                        else:
                            st.error("Please confirm removal.")
    else:
        st.info("Cannot remove the only admin account.")
else:
    st.info("No employees to remove.")
