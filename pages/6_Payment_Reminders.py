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
from utils.gmail_sender import get_gmail_service, send_email
from utils.supabase_db import append_record, fetch_sheet_data_by_name, get_or_create_worksheet
from utils.ui import get_spreadsheet_connection, init_page
from utils.whatsapp_sender import generate_whatsapp_link

EMAIL_TYPE = "Payment Reminder"


def parse_date(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def to_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def build_reminder_body(name, amount, due_date):
    return (
        f"Dear {name},\n\n"
        "I hope this message finds you well.\n\n"
        "This is a gentle reminder that Invoice [Invoice Number] amounting to "
        f"Rs {amount:,.2f} was due on {due_date}. As per our records, the payment is currently outstanding.\n\n"
        "We kindly request you to arrange the payment at your earliest convenience. "
        "Should you have already processed this payment, please disregard this notice.\n\n"
        "For any queries regarding this invoice, feel free to reach out to us directly.\n\n"
        "Warm regards,\n"
        "Satyam Machinery Parts\n"
        "Bhilwara, Rajasthan\n"
        "Contact: [Your Phone Number]"
    )


def log_email(email_log_ws, row):
    append_record(email_log_ws, EMAIL_LOG_HEADERS, row)


init_page("Payment Reminders")
st.title("Payment Reminders")

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

payments_ws = get_or_create_worksheet(spreadsheet, PAYMENTS_TAB, PAYMENTS_HEADERS)
contacts_ws = get_or_create_worksheet(spreadsheet, CONTACTS_TAB, CONTACTS_HEADERS)
email_log_ws = get_or_create_worksheet(spreadsheet, EMAIL_LOG_TAB, EMAIL_LOG_HEADERS)

payments = fetch_sheet_data_by_name(PAYMENTS_TAB, PAYMENTS_HEADERS)
contacts = fetch_sheet_data_by_name(CONTACTS_TAB, CONTACTS_HEADERS)

contacts_by_name = {c.get("Name", "").strip().lower(): c for c in contacts}

rows = []
for payment in payments:
    status = payment.get("Status", "").strip().lower()
    if status not in {"pending", "overdue"}:
        continue

    due = parse_date(payment.get("Due Date", ""))
    if due is None:
        continue

    name = payment.get("Customer Name", "").strip()
    contact = contacts_by_name.get(name.lower(), {})
    email = contact.get("Email", "").strip()
    phone = contact.get("Phone", "").strip()
    business_name = contact.get("Business Name", "").strip()
    days_overdue = max((date.today() - due).days, 0)

    rows.append(
        {
            "Select": False,
            "Name": name,
            "Business Name": business_name,
            "Email": email,
            "Phone": phone,
            "Invoice Number": payment.get("Invoice Number", "").strip(),
            "Amount Due": to_float(payment.get("Amount", "0")),
            "Due Date": due.isoformat(),
            "Days Overdue": days_overdue,
        }
    )

st.subheader("Pending / Overdue Customers")
if not rows:
    st.info("No pending or overdue payments found.")
    st.stop()

reminders_df = pd.DataFrame(rows)
edited_df = st.data_editor(
    reminders_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    disabled=["Name", "Email", "Phone", "Invoice Number", "Amount Due", "Due Date", "Days Overdue", "Business Name"],
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", default=False),
        "Amount Due": st.column_config.NumberColumn("Amount Due", format="%.2f"),
    },
)

selected = edited_df[edited_df["Select"]]
st.caption(f"Selected recipients: {len(selected)}")

st.markdown("---")
st.subheader("Email Template")

default_subject = "Payment Due Reminder – Invoice [Invoice Number] | [Business Name]"
default_body = (
    "Dear [Customer Name],\n\n"
    "I hope this message finds you well.\n\n"
    "This is a gentle reminder that Invoice [Invoice Number] amounting to ₹[Amount] "
    "was due on [Due Date]. As per our records, the payment is currently outstanding.\n\n"
    "We kindly request you to arrange the payment at your earliest convenience. "
    "Should you have already processed this payment, please disregard this notice.\n\n"
    "For any queries regarding this invoice, feel free to reach out to us directly.\n\n"
    "Warm regards,\n"
    "Satyam Machinery Parts\n"
    "Bhilwara, Rajasthan\n"
    "Contact: [Your Phone Number]"
)

subject_template = st.text_input("Subject", value=default_subject)
body_template = st.text_area("Body", value=default_body, height=220)
company_phone = st.text_input("Your Phone Number", value="+91-XXXXXXXXXX")

whatsapp_template = (
    "Dear [Customer Name],\n"
    "This is a reminder from Satyam Machinery Parts.\n"
    "Invoice [Invoice Number] of ₹[Amount] was due on [Due Date].\n"
    "Kindly clear the outstanding amount at the earliest.\n"
    "For queries, contact us on WhatsApp.\n"
    "Thank you,\n"
    "Satyam Machinery Parts, Bhilwara"
)

st.markdown("---")
st.subheader("Send Reminders")
send_mode = st.radio(
    "Choose sending method",
    options=["Email Only", "WhatsApp Only", "Both Email & WhatsApp"],
    horizontal=True,
)


def personalize(text, row):
    result = text
    result = result.replace("[Invoice Number]", str(row["Invoice Number"]))
    result = result.replace("[Customer Name]", str(row["Name"]))
    result = result.replace("[Business Name]", str(row["Business Name"]))
    result = result.replace("[Amount]", f"{float(row['Amount Due']):,.2f}")
    result = result.replace("[Due Date]", str(row["Due Date"]))
    result = result.replace("[Your Phone Number]", company_phone)
    return result


if st.button("Send Reminders", type="primary"):
    if selected.empty:
        st.error("Please select at least one customer.")
        st.stop()

    result_rows = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if send_mode in ["Email Only", "Both Email & WhatsApp"]:
        try:
            gmail_service = get_gmail_service()
        except Exception as exc:
            st.error(f"Gmail authentication failed: {exc}")
            st.stop()

    for _, row in selected.iterrows():
        recipient_name = str(row["Name"]).strip()
        recipient_email = str(row["Email"]).strip()
        recipient_phone = str(row["Phone"]).strip()
        subject = personalize(subject_template, row)
        body = personalize(body_template, row)
        whatsapp_msg = personalize(whatsapp_template, row)

        email_status = "Not Sent"
        email_error = ""
        whatsapp_status = "Not Sent"
        whatsapp_error = ""

        if send_mode in ["Email Only", "Both Email & WhatsApp"]:
            if not recipient_email:
                email_error = "Missing recipient email in Customers & Leads sheet."
                st.error(f"{recipient_name}: {email_error}")
                log_email(
                    email_log_ws,
                    {
                        "Timestamp": timestamp,
                        "Email Type": EMAIL_TYPE,
                        "Recipient Name": recipient_name,
                        "Recipient Email": "",
                        "Subject": subject,
                        "Status": "Failed",
                        "Error": email_error,
                    },
                )
                email_status = "Failed"
            else:
                try:
                    send_email(gmail_service, recipient_email, subject, body)
                    st.success(f"Email sent to {recipient_name} ({recipient_email})")
                    log_email(
                        email_log_ws,
                        {
                            "Timestamp": timestamp,
                            "Email Type": EMAIL_TYPE,
                            "Recipient Name": recipient_name,
                            "Recipient Email": recipient_email,
                            "Subject": subject,
                            "Status": "Sent",
                            "Error": "",
                        },
                    )
                    email_status = "Sent"
                except Exception as exc:
                    email_error = str(exc)
                    st.error(f"Email failed for {recipient_name}: {email_error}")
                    log_email(
                        email_log_ws,
                        {
                            "Timestamp": timestamp,
                            "Email Type": EMAIL_TYPE,
                            "Recipient Name": recipient_name,
                            "Recipient Email": recipient_email,
                            "Subject": subject,
                            "Status": "Failed",
                            "Error": email_error,
                        },
                    )
                    email_status = "Failed"

        if send_mode in ["WhatsApp Only", "Both Email & WhatsApp"]:
            if not recipient_phone:
                whatsapp_error = "Missing recipient phone number in Customers & Leads sheet."
                st.error(f"{recipient_name}: {whatsapp_error}")
                whatsapp_status = "Failed"
            else:
                whatsapp_link = generate_whatsapp_link(recipient_phone, whatsapp_msg)
                st.link_button("📲 Send via WhatsApp", whatsapp_link)
                whatsapp_status = "Link Ready"

        result_rows.append(
            {
                "Recipient": recipient_name,
                "Email Status": email_status,
                "WhatsApp Status": whatsapp_status,
                "Phone": recipient_phone,
                "Email": recipient_email,
            }
        )

    st.markdown("### Send Results")
    results_df = pd.DataFrame(result_rows)
    with st.expander(f"📋 Sending Results ({len(result_rows)} records) — click to expand", expanded=False):
        st.dataframe(results_df, use_container_width=True, hide_index=True)
