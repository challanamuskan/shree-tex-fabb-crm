from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.auth import require_login, is_admin
require_login()

from utils.constants import PAYMENTS_HEADERS, PAYMENTS_TAB
from utils.sheets_db import (
    append_record,
    delete_record,
    get_cached_records_by_title,
    get_or_create_worksheet,
    update_record,
)
from utils.file_handler import upload_and_scan_widget
from utils.ui import (
    get_spreadsheet_connection,
    init_page,
)

STATUS_OPTIONS = ["Paid", "Pending", "Overdue"]


def to_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def parse_date(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return date.today()


def parse_scanned_date(value):
    value_str = str(value).strip()
    if not value_str:
        return date.today()

    date_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%m-%y",
        "%d/%m/%y",
        "%d %b %Y",
        "%d %B %Y",
        "%d %b %y",
    ]
    for fmt in date_formats:
        try:
            return datetime.strptime(value_str, fmt).date()
        except ValueError:
            continue
    return date.today()


def is_overdue(record):
    due = parse_date(record.get("Due Date", ""))
    status = record.get("Status", "").strip().lower()
    return due < date.today() and status != "paid"


init_page("Payments")
st.title("Payments")

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

worksheet = get_or_create_worksheet(spreadsheet, PAYMENTS_TAB, PAYMENTS_HEADERS)
records = get_cached_records_by_title(worksheet.title, PAYMENTS_HEADERS)

st.subheader("Payment Dues")
if records:
    df = pd.DataFrame(records).drop(columns=["_row", "Receipt_Document"], errors="ignore")

    def highlight_overdue(row):
        record = row.to_dict()
        if is_overdue(record):
            return ["background-color: #fecaca; color: #7f1d1d;"] * len(row)
        return [""] * len(row)

    styled = df.style.apply(highlight_overdue, axis=1)
    
    with st.expander(f"📋 View All Payment Dues ({len(records)} records) — click to expand", expanded=False):
        st.dataframe(styled, use_container_width=True, hide_index=True)

    overdue_count = sum(1 for r in records if is_overdue(r))
    pending_amount = sum(
        to_float(r.get("Amount", "0"))
        for r in records
        if r.get("Status", "").strip().lower() != "paid"
    )
    st.caption(f"Pending amount: Rs {pending_amount:,.2f} | Overdue invoices: {overdue_count}")
else:
    st.info("No payment records found.")

st.markdown("---")
st.subheader("Add Payment")
with st.form("add_payment_form", clear_on_submit=True):
    bill_b64, scan_data = upload_and_scan_widget("Payment Receipt", "payment_receipt")
    scanned_amount = to_float(scan_data.get("amount", ""))
    scanned_due_date = parse_scanned_date(scan_data.get("date", ""))

    c1, c2 = st.columns(2)
    with c1:
        customer_name = st.text_input("Customer Name", value=scan_data.get("party_name", ""))
        invoice_number = st.text_input("Invoice Number", value=scan_data.get("invoice_number", ""))
        amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f", value=scanned_amount)
    with c2:
        due_date = st.date_input("Due Date", value=scanned_due_date)
        status = st.selectbox("Status", STATUS_OPTIONS, index=1)

    add_submit = st.form_submit_button("Add Payment")
    if add_submit:
        if not customer_name.strip() or not invoice_number.strip():
            st.error("Customer Name and Invoice Number are required.")
        else:
            effective_status = status
            if status != "Paid" and due_date < date.today():
                effective_status = "Overdue"

            payload = {
                "Customer Name": customer_name.strip(),
                "Invoice Number": invoice_number.strip(),
                "Amount": f"{float(amount):.2f}",
                "Due Date": due_date.isoformat(),
                "Status": effective_status,
                "Receipt_Document": bill_b64,
            }
            try:
                append_record(worksheet, PAYMENTS_HEADERS, payload)
                st.success("Payment record added successfully.")
                st.rerun()
            except Exception as exc:
                st.error(f"Error adding payment: {exc}")

st.markdown("---")
st.subheader("Edit / Delete Payment")
if records:
    if is_admin():
        option_map = {
            f"{r['Invoice Number']} | {r['Customer Name']}": r
            for r in records
        }
        selected_key = st.selectbox("Select payment", options=list(option_map.keys()))
        selected = option_map[selected_key]

        with st.form("edit_payment_form"):
            c1, c2 = st.columns(2)
            with c1:
                e_customer_name = st.text_input("Customer Name", value=selected["Customer Name"])
                e_invoice_number = st.text_input("Invoice Number", value=selected["Invoice Number"])
                e_amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    value=to_float(selected["Amount"]),
                )
            with c2:
                e_due_date = st.date_input("Due Date", value=parse_date(selected["Due Date"]))
                existing_status = selected["Status"] if selected["Status"] in STATUS_OPTIONS else "Pending"
                e_status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(existing_status))

            update_submit = st.form_submit_button("Update Payment")
            if update_submit:
                if not e_customer_name.strip() or not e_invoice_number.strip():
                    st.error("Customer Name and Invoice Number are required.")
                else:
                    effective_status = e_status
                    if e_status != "Paid" and e_due_date < date.today():
                        effective_status = "Overdue"

                    payload = {
                        "Customer Name": e_customer_name.strip(),
                        "Invoice Number": e_invoice_number.strip(),
                        "Amount": f"{float(e_amount):.2f}",
                        "Due Date": e_due_date.isoformat(),
                        "Status": effective_status,
                        "Receipt_Document": selected.get("Receipt_Document", ""),
                    }
                    try:
                        update_record(worksheet, selected["_row"], PAYMENTS_HEADERS, payload)
                        st.success("Payment updated successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error updating payment: {exc}")

        confirm_delete = st.checkbox("Confirm delete selected payment")
        if st.button("Delete Payment", type="secondary"):
            if not confirm_delete:
                st.error("Please confirm deletion first.")
            else:
                try:
                    delete_record(worksheet, selected["_row"])
                    st.success("Payment deleted successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error deleting payment: {exc}")
    else:
        st.warning("🔐 Admin login required to edit or delete records.")
else:
    st.info("Add a payment to enable edit/delete actions.")
