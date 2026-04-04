import calendar
from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.auth import require_login, is_admin
require_login()

from utils.constants import (
    CONTACTS_HEADERS,
    CONTACTS_TAB,
    EMAIL_LOG_HEADERS,
    EMAIL_LOG_TAB,
    PAYMENTS_HEADERS,
    PAYMENTS_TAB,
)
from utils.email_alerts import (
    get_low_stock_auto_alert_setting,
    send_low_stock_email_alert,
    set_low_stock_auto_alert_setting,
)
from utils.sheets_db import fetch_sheet_data_by_name, get_or_create_worksheet
from utils.ui import get_spreadsheet_connection, init_page


def parse_date(value):
    text = str(value).strip()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    if len(text) >= 10:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    return None


def to_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def previous_month(first_day):
    if first_day.month == 1:
        return date(first_day.year - 1, 12, 1)
    return date(first_day.year, first_day.month - 1, 1)


def next_month(first_day):
    if first_day.month == 12:
        return date(first_day.year + 1, 1, 1)
    return date(first_day.year, first_day.month + 1, 1)


init_page("Calendar")
st.title("Calendar")

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

contacts_ws = get_or_create_worksheet(spreadsheet, CONTACTS_TAB, CONTACTS_HEADERS)
payments_ws = get_or_create_worksheet(spreadsheet, PAYMENTS_TAB, PAYMENTS_HEADERS)
email_log_ws = get_or_create_worksheet(spreadsheet, EMAIL_LOG_TAB, EMAIL_LOG_HEADERS)

contacts = fetch_sheet_data_by_name(CONTACTS_TAB, CONTACTS_HEADERS)
payments = fetch_sheet_data_by_name(PAYMENTS_TAB, PAYMENTS_HEADERS)
email_logs = fetch_sheet_data_by_name(EMAIL_LOG_TAB, EMAIL_LOG_HEADERS)

state_key = "calendar_first_day"
if state_key not in st.session_state:
    st.session_state[state_key] = date.today().replace(day=1)

control_col_1, control_col_2, control_col_3 = st.columns([1, 2, 1])
with control_col_1:
    if st.button("◀ Previous Month"):
        st.session_state[state_key] = previous_month(st.session_state[state_key])
with control_col_3:
    if st.button("Next Month ▶"):
        st.session_state[state_key] = next_month(st.session_state[state_key])

first_day = st.session_state[state_key]
st.markdown(f"### {first_day.strftime('%B %Y')}")

events_by_date = {}

for contact in contacts:
    follow_up_date = parse_date(contact.get("Follow-up Date", ""))
    if not follow_up_date:
        continue

    customer_name = contact.get("Name", "").strip()
    business_name = contact.get("Business Name", "").strip()
    phone = contact.get("Phone", "").strip()
    events_by_date.setdefault(follow_up_date, []).append(
        {
            "Type": "Follow-up",
            "Type Color": "green",
            "Details": f"{customer_name} — {business_name} — {phone}",
            "Customer Name": customer_name,
            "Business Name": business_name,
            "Phone": phone,
        }
    )

for payment in payments:
    due_date = parse_date(payment.get("Due Date", ""))
    if not due_date:
        continue

    customer_name = payment.get("Customer Name", "").strip()
    amount = to_float(payment.get("Amount", "0"))
    invoice_number = payment.get("Invoice Number", "").strip()
    events_by_date.setdefault(due_date, []).append(
        {
            "Type": "Payment Due",
            "Type Color": "red",
            "Details": f"{customer_name} — ₹{amount:,.2f} — Invoice #{invoice_number}",
            "Customer Name": customer_name,
            "Amount": f"₹{amount:,.2f}",
            "Invoice Number": invoice_number,
            "Status": payment.get("Status", "").strip(),
        }
    )

for log in email_logs:
    log_date = parse_date(log.get("Timestamp", ""))
    email_type = log.get("Email Type", "").strip().lower()
    if not log_date or not ("payment" in email_type and "reminder" in email_type):
        continue

    recipient_name = log.get("Recipient Name", "").strip()
    events_by_date.setdefault(log_date, []).append(
        {
            "Type": "Payment Reminder Sent",
            "Type Color": "blue",
            "Details": f"Reminder sent to {recipient_name}",
            "Customer Name": recipient_name,
            "Subject": log.get("Subject", "").strip(),
            "Status": log.get("Status", "").strip(),
        }
    )

month_followups = 0
month_payments = 0
month_reminders = 0
for event_date, events in events_by_date.items():
    if event_date.year == first_day.year and event_date.month == first_day.month:
        month_followups += sum(1 for e in events if e["Type"] == "Follow-up")
        month_payments += sum(1 for e in events if e["Type"] == "Payment Due")
        month_reminders += sum(1 for e in events if e["Type"] == "Payment Reminder Sent")

sum_col_1, sum_col_2, sum_col_3 = st.columns(3)
sum_col_1.metric("Follow-ups This Month", month_followups)
sum_col_2.metric("Payments Due This Month", month_payments)
sum_col_3.metric("Reminders Sent This Month", month_reminders)
st.caption(
    f"{month_followups} follow-ups this month | {month_payments} payments due this month | {month_reminders} reminders sent"
)

st.markdown(":green[Green = Follow-ups]  |  :red[Red = Payment Due]  |  :blue[Blue = Payment Reminders Sent]")

weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
header_cols = st.columns(7)
for idx, weekday in enumerate(weekday_names):
    header_cols[idx].markdown(f"**{weekday}**")

month_matrix = calendar.monthcalendar(first_day.year, first_day.month)

if "selected_calendar_date" not in st.session_state:
    st.session_state["selected_calendar_date"] = first_day

for week_index, week in enumerate(month_matrix):
    week_cols = st.columns(7)
    for day_idx, day_num in enumerate(week):
        with week_cols[day_idx]:
            if day_num == 0:
                st.markdown(" ")
                continue

            current_date = date(first_day.year, first_day.month, day_num)
            day_events = events_by_date.get(current_date, [])
            followups_count = sum(1 for e in day_events if e["Type"] == "Follow-up")
            payments_count = sum(1 for e in day_events if e["Type"] == "Payment Due")
            reminders_count = sum(1 for e in day_events if e["Type"] == "Payment Reminder Sent")

            if st.button(str(day_num), key=f"day_{week_index}_{day_idx}_{current_date.isoformat()}"):
                st.session_state["selected_calendar_date"] = current_date

            if followups_count:
                st.markdown(f":green[Follow-ups: {followups_count}]")
            if payments_count:
                st.markdown(f":red[Payments: {payments_count}]")
            if reminders_count:
                st.markdown(f":blue[Reminders: {reminders_count}]")
            if not day_events:
                st.caption("No events")

selected_date = st.session_state.get("selected_calendar_date", first_day)
st.markdown("---")
st.subheader(f"Events on {selected_date.strftime('%d %b %Y')}")
selected_events = events_by_date.get(selected_date, [])

if selected_events:
    events_df = pd.DataFrame(selected_events)
    preferred_cols = [
        "Type",
        "Details",
        "Customer Name",
        "Business Name",
        "Phone",
        "Amount",
        "Invoice Number",
        "Subject",
        "Status",
    ]
    output_cols = [c for c in preferred_cols if c in events_df.columns]
    st.dataframe(events_df[output_cols], use_container_width=True, hide_index=True)
else:
    st.info("No events for this date.")

st.markdown("---")
st.subheader("Low Stock Alerts")

if is_admin():
    current_auto = get_low_stock_auto_alert_setting()
    auto_enabled = st.toggle("Auto-send alerts on 1st and 15th of every month", value=current_auto)
    if auto_enabled != current_auto:
        if set_low_stock_auto_alert_setting(auto_enabled):
            st.success("Auto-alert setting saved.")
        else:
            st.error("Could not save auto-alert setting.")

    if st.button("📧 Send Low Stock Alert Now"):
        ok, count, message = send_low_stock_email_alert()
        if ok:
            if count > 0:
                st.success(f"Low stock alert email sent for {count} items.")
            else:
                st.info(message)
        else:
            st.error(f"Failed to send low stock alert email: {message}")
else:
    st.info("Admin access required to manage low stock email alerts.")
