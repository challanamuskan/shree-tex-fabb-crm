import streamlit as st
from datetime import datetime, timedelta
import random

from utils.auth import verify_login, is_logged_in
from utils.gmail_sender import send_email, get_gmail_service

st.set_page_config(
    page_title="Satyam Tex Fabb Login",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Redirect if already logged in
if is_logged_in():
    st.switch_page("app.py")

st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 50px auto;
        padding: 40px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        background: white;
    }
    .login-title {
        text-align: center;
        font-size: 28px;
        margin-bottom: 10px;
    }
    .login-subtitle {
        text-align: center;
        color: #6B7280;
        margin-bottom: 30px;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("logo.png", width=120)
    st.markdown("<h2 style='text-align: center; margin-top: 0;'>Satyam Tex Fabb</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280;'>Bhilwara, Rajasthan</p>", unsafe_allow_html=True)

st.markdown("---")

# Tabs for Login and Forgot Password
login_tab, forgot_tab = st.tabs(["Login", "Forgot Password?"])

with login_tab:
    with st.form("login_form"):
        username = st.text_input("Employee ID / Username", placeholder="Enter your employee ID")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        login_button = st.form_submit_button("🔓 Login", use_container_width=True)

        if login_button:
            if not username.strip() or not password.strip():
                st.error("Please enter both username and password.")
            else:
                user_info = verify_login(username.strip(), password.strip())
                if user_info:
                    # Set session state
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user_info["username"]
                    st.session_state["user_role"] = user_info["role"]
                    st.session_state["user_fullname"] = user_info["full_name"]
                    st.session_state["user_email"] = user_info["email"]

                    if user_info["must_change"]:
                        st.session_state["force_change_password"] = True
                        st.success("Login successful! You must change your password.")
                        st.switch_page("pages/9_Change_Password.py")
                    else:
                        st.success("Login successful! Redirecting...")
                        st.switch_page("app.py")
                else:
                    st.error("❌ Invalid username or password.")

with forgot_tab:
    st.markdown("### Reset Your Password")

    reset_email = st.text_input("Registered Email Address", placeholder="gmail@example.com")

    if st.button("Send Reset Code", use_container_width=True):
        if not reset_email.strip():
            st.error("Please enter your registered email.")
        else:
            # Generate a 6-digit reset code
            reset_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
            reset_expiry = datetime.now() + timedelta(minutes=10)

            # Store in session
            st.session_state["reset_code"] = reset_code
            st.session_state["reset_code_expiry"] = reset_expiry
            st.session_state["reset_email"] = reset_email

            # Try to send email
            try:
                gmail_service = get_gmail_service()
                email_body = f"""
Hello,

Your password reset code is: {reset_code}

This code will expire in 10 minutes.

If you did not request this, please ignore this email.

Best regards,
Satyam Tex Fabb Team
Bhilwara, Rajasthan
"""
                send_email(
                    gmail_service,
                    reset_email,
                    "Password Reset Code - Satyam Tex Fabb CRM",
                    email_body,
                )
                st.success("✅ Reset code sent to your email. Check your inbox (or spam folder).")
                st.session_state["show_reset_form"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Could not send reset code: {e}")

    # Show reset code input if code was requested
    if st.session_state.get("show_reset_form", False):
        st.markdown("---")
        st.markdown("### Enter Reset Code")

        col1, col2 = st.columns([2, 1])
        with col1:
            entered_code = st.text_input("6-Digit Reset Code", placeholder="000000")
        with col2:
            st.write("")
            st.write("")
            verify_code_button = st.button("Verify", use_container_width=True)

        if verify_code_button:
            if not entered_code.strip():
                st.error("Please enter the reset code.")
            elif datetime.now() > st.session_state.get("reset_code_expiry", datetime.now()):
                st.error("❌ Reset code expired. Please request a new one.")
                st.session_state.pop("show_reset_form", None)
                st.rerun()
            elif entered_code.strip() == st.session_state.get("reset_code", ""):
                st.success("✅ Code verified! You can now set a new password.")
                st.session_state["reset_code_verified"] = True
                st.rerun()
            else:
                st.error("❌ Incorrect reset code.")

        if st.session_state.get("reset_code_verified", False):
            st.markdown("---")
            st.markdown("### Set New Password")

            with st.form("set_new_password_form"):
                new_password = st.text_input("New Password", type="password", placeholder="Enter new password")
                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Confirm new password",
                )
                set_password_button = st.form_submit_button(
                    "Update Password",
                    use_container_width=True,
                )

                if set_password_button:
                    if not new_password or not confirm_password:
                        st.error("Please fill in both password fields.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(new_password) < 8:
                        st.error("Password must be at least 8 characters long.")
                    else:
                        # Update password in auth system
                        from utils.auth import hash_password, update_password_hash, verify_login

                        # Find the username for this email
                        from utils.auth import get_all_users
                        users = get_all_users()
                        matching_user = None
                        for user in users:
                            if user.get("Email", "").strip() == st.session_state.get("reset_email", "").strip():
                                matching_user = user
                                break

                        if matching_user:
                            if update_password_hash(
                                matching_user["Username"],
                                hash_password(new_password),
                            ):
                                st.success("✅ Password updated successfully! You can now login with your new password.")
                                # Clear reset state
                                for key in [
                                    "show_reset_form",
                                    "reset_code",
                                    "reset_code_expiry",
                                    "reset_email",
                                    "reset_code_verified",
                                ]:
                                    st.session_state.pop(key, None)
                                st.rerun()
                            else:
                                st.error("Failed to update password. Please try again.")
                        else:
                            st.error("Email not found in system.")
