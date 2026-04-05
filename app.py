from datetime import date, datetime

import pandas as pd
import streamlit as st
from utils.auth import is_logged_in, is_admin, logout

st.set_page_config(layout="wide", page_title="Satyam Tex Fabb CRM", initial_sidebar_state="collapsed")

# Check if logged in - redirect to login if not
if not is_logged_in():
    st.switch_page("pages/0_🔐_Login.py")

from utils.constants import (
    CONTACTS_TAB,
    EMAIL_LOG_TAB,
    PARTS_TAB,
    PAYMENTS_TAB,
    PURCHASE_ORDERS_TAB,
)
from utils.email_alerts import send_low_stock_email_alert
from utils.sheets_db import fetch_tab
from utils.ui import get_spreadsheet_connection, init_page


def to_int(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def to_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def to_date(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def is_overdue(payment_record):
    due = to_date(payment_record.get("Due Date", ""))
    status = payment_record.get("Status", "").strip().lower()
    return bool(due and due < date.today() and status != "paid")


def is_open_lead(contact_record):
    status = contact_record.get("Lead Status", "").strip().lower()
    return status not in {"closed", "converted", "won", "lost"}


if "alert_sent_today" not in st.session_state:
    st.session_state.alert_sent_today = False

today = date.today()
if today.day in [1, 15] and not st.session_state.alert_sent_today:
    success, msg = send_low_stock_email_alert()
    st.session_state.alert_sent_today = True


init_page("Dashboard")

# Sidebar setup
with st.sidebar:
    st.sidebar.write(f"👤 {st.session_state.get('user_fullname', 'User')}")
    st.caption(f"Role: {st.session_state.get('user_role', 'unknown').capitalize()}")
    st.markdown("---")
    if st.sidebar.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🔑 Change Password", use_container_width=True):
        st.switch_page("pages/11_Change_Password.py")
    if st.button("🚪 Logout", use_container_width=True):
        logout()
        st.rerun()
    st.sidebar.image("logo.png", width=80)
    st.sidebar.markdown("### Satyam Tex Fabb")
    st.caption("📍 Bhilwara, Rajasthan")
    st.caption(f"📅 {date.today().strftime('%A, %B %d, %Y')}")
    st.markdown("---")

# Header
col1, col2 = st.columns([1, 6])
with col1:
    st.image("logo.png", width=80)
with col2:
    st.markdown("# Satyam Tex Fabb")
    st.markdown("*Bhilwara, Rajasthan · Since 1994*")
st.markdown("---")

today = date.today().strftime("%A, %B %d, %Y")
hour = datetime.now().hour
greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
st.markdown(f"<p style='color: #6B7280; font-size: 16px;'>{greeting}! Here's your business overview for <strong>{today}</strong></p>", unsafe_allow_html=True)
st.markdown("---")

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

parts = fetch_tab(PARTS_TAB)
contacts = fetch_tab(CONTACTS_TAB)
payments = fetch_tab(PAYMENTS_TAB)
pos = fetch_tab(PURCHASE_ORDERS_TAB)

low_stock_parts = [
    part
    for part in parts
    if to_int(part.get("Quantity", 0)) < to_int(part.get("Reorder_Level", 0))
]

pending_payments = [payment for payment in payments if payment.get("Status", "").strip().lower() != "paid"]
overdue_payments = [payment for payment in payments if is_overdue(payment)]
open_leads = [contact for contact in contacts if is_open_lead(contact)]

pending_amount = sum(to_float(payment.get("Amount", 0)) for payment in pending_payments)

m1, m2, m3, m4 = st.columns(4)
m1.metric("📦 Total Parts", len(parts))
m2.metric("⚠️ Low Stock Alerts", len(low_stock_parts))
m3.metric("💰 Pending Payments", len(pending_payments), f"Rs {pending_amount:,.2f}")
m4.metric("👥 Open Leads", len(open_leads))

st.markdown("---")

primary_col, secondary_col = st.columns(2)

with primary_col:
    st.markdown("### 📦 Low Stock Parts")
    try:
        all_parts = fetch_tab("Parts")
        if all_parts:
            parts_df = pd.DataFrame(all_parts)

            # Only calculate low stock if both columns exist and have numeric values
            if "Quantity" in parts_df.columns and "Reorder_Level" in parts_df.columns:
                def safe_int(val):
                    try:
                        return int(float(str(val).strip()))
                    except:
                        return 0

                parts_df["_qty"] = parts_df["Quantity"].apply(safe_int)
                parts_df["_reorder"] = parts_df["Reorder_Level"].apply(safe_int)

                # Only flag as low stock if Reorder_Level is actually set (> 0)
                low_df = parts_df[
                    (parts_df["_reorder"] > 0)
                    & (parts_df["_qty"] <= parts_df["_reorder"])
                ]

                if low_df.empty:
                    st.info("✅ No low stock alerts — all parts are above reorder levels.")
                else:
                    for col in ["Category", "Part_Name", "Quantity", "Reorder_Level"]:
                        if col not in low_df.columns:
                            low_df[col] = ""
                    st.dataframe(
                        low_df[["Category", "Part_Name", "Quantity", "Reorder_Level"]],
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.info("✅ No reorder levels configured yet. Set them in Stock Manager to enable alerts.")
        else:
            st.info("No parts data found.")
    except Exception:
        st.info("✅ Low stock data unavailable — will display once reorder levels are configured.")

    st.markdown("### 👥 Open Leads")
    if open_leads:
        leads_df = pd.DataFrame(open_leads)[
            ["Name", "Business Name", "Phone", "Machine Type", "Lead Status", "Follow-up Date"]
        ]
        st.dataframe(leads_df, use_container_width=True, hide_index=True)
    else:
        st.success("No open leads.")

with secondary_col:
    st.markdown("### 💰 Overdue Payments")
    if overdue_payments:
        overdue_df = pd.DataFrame(overdue_payments)[
            ["Customer Name", "Invoice Number", "Amount", "Due Date", "Status"]
        ]
        st.dataframe(overdue_df, use_container_width=True, hide_index=True)
        st.error("Overdue payment(s) need attention.")
    else:
        st.success("No overdue payments.")

    st.markdown("### 🚚 Purchase Order Snapshot")
    if pos:
        po_df = pd.DataFrame(pos)[
            ["Supplier", "Part Name", "Quantity Ordered", "Order Date", "Expected Delivery", "Status"]
        ]
        st.dataframe(po_df, use_container_width=True, hide_index=True)
    else:
        st.info("No purchase orders yet.")

st.markdown("---")

email_log = fetch_tab(EMAIL_LOG_TAB)

if email_log:
    st.markdown("### 📧 Recent Email Activity")
    recent_emails = email_log[-5:] if len(email_log) > 5 else email_log
    recent_df = pd.DataFrame(reversed(recent_emails))[
        ["Timestamp", "Email Type", "Recipient Email", "Subject", "Status"]
    ]
    st.dataframe(recent_df, use_container_width=True, hide_index=True)
else:
    st.info("No email activity yet.")

st.markdown("---")
st.caption(
    "Use the left sidebar to switch pages: Stock Manager, Sales, Purchases, Returns, Customers & Leads, "
    "Payments, Purchase Orders, Payment Reminders, Promotional Emails, Calendar, MIS System, Data Export & Import."
)
