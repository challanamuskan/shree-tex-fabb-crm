import streamlit as st
from utils.auth import require_login, is_admin, hash_password, verify_login, update_password_hash, logout

require_login()

st.set_page_config(
    page_title="Change Password - Satyam Tex Fabb",
    layout="centered",
)

st.markdown("# 🔑 Change Password")
st.markdown("---")

if st.session_state.get("force_change_password", False):
    st.warning("⚠️ You are required to change your password before proceeding.")

with st.form("change_password_form"):
    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    submit_button = st.form_submit_button("Update Password", use_container_width=True)

    if submit_button:
        username = st.session_state.get("username", "")

        if not all([current_password, new_password, confirm_password]):
            st.error("All fields are required.")
        elif len(new_password) < 8:
            st.error("New password must be at least 8 characters long.")
        elif new_password != confirm_password:
            st.error("New passwords do not match.")
        else:
            # Verify current password
            user_info = verify_login(username, current_password)
            if not user_info:
                st.error("Current password is incorrect.")
            else:
                # Update password
                if update_password_hash(username, hash_password(new_password)):
                    st.success("✅ Password updated successfully!")
                    st.session_state.pop("force_change_password", None)
                    st.balloons()

                    import time
                    time.sleep(1)
                    st.switch_page("app.py")
                else:
                    st.error("Failed to update password. Please try again.")
