from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.constants import (
    CONTACTS_HEADERS,
    CONTACTS_TAB,
    EMAIL_LOG_HEADERS,
    EMAIL_LOG_TAB,
    PARTS_HEADERS,
    PARTS_TAB,
    PAYMENTS_HEADERS,
    PAYMENTS_TAB,
    PURCHASE_ORDERS_HEADERS,
    PURCHASE_ORDERS_TAB,
)
from utils.sheets_db import get_or_create_worksheet, read_records
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


init_page("Dashboard")

# Sidebar setup
with st.sidebar:
    st.markdown("### ⚙️ Shree Tex Fabb")
    st.caption("📍 Bhilwara, Rajasthan")
    st.caption(f"📅 {date.today().strftime('%A, %B %d, %Y')}")
    st.markdown("---")

# Header
st.markdown("# ⚙️ Shree Tex Fabb")
st.markdown("<p style='color: #6B7280; margin-top: -20px;'>Bhilwara, Rajasthan</p>", unsafe_allow_html=True)
st.markdown("---")

today = date.today().strftime("%A, %B %d, %Y")
hour = datetime.now().hour
greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
st.markdown(f"<p style='color: #6B7280; font-size: 16px;'>{greeting}! Here's your business overview for <strong>{today}</strong></p>", unsafe_allow_html=True)
st.markdown("---")

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

parts_ws = get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS)
contacts_ws = get_or_create_worksheet(spreadsheet, CONTACTS_TAB, CONTACTS_HEADERS)
payments_ws = get_or_create_worksheet(spreadsheet, PAYMENTS_TAB, PAYMENTS_HEADERS)
pos_ws = get_or_create_worksheet(spreadsheet, PURCHASE_ORDERS_TAB, PURCHASE_ORDERS_HEADERS)

parts = read_records(parts_ws, PARTS_HEADERS)
contacts = read_records(contacts_ws, CONTACTS_HEADERS)
payments = read_records(payments_ws, PAYMENTS_HEADERS)
pos = read_records(pos_ws, PURCHASE_ORDERS_HEADERS)

low_stock_parts = [
    part
    for part in parts
    if to_int(part.get("Quantity", 0)) < to_int(part.get("Reorder Level", 0))
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
    if low_stock_parts:
        low_df = pd.DataFrame(low_stock_parts)[
            ["Part Number", "Part Name", "Quantity", "Reorder Level", "Supplier Name"]
        ]
        st.dataframe(low_df, use_container_width=True, hide_index=True)
    else:
        st.success("No low stock alerts.")

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

email_log_ws = get_or_create_worksheet(spreadsheet, EMAIL_LOG_TAB, EMAIL_LOG_HEADERS)
email_log = read_records(email_log_ws, EMAIL_LOG_HEADERS)

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
    "Use the left sidebar to switch pages: Stock Manager, Customers & Leads, Payments, "
    "Purchase Orders, Payment Reminders, Promotional Emails, Calendar, MIS System."
)
