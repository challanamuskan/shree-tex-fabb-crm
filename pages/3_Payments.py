from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.auth import require_login, is_admin
from utils.supabase_db import fetch_table, insert_record, update_record, delete_record
from utils.ui import init_page

require_login()
init_page("Payments")
st.title("Payments")

STATUS_OPTIONS = ["Pending", "Paid", "Overdue"]


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


def is_overdue(record):
    due = parse_date(record.get("due_date", ""))
    status = str(record.get("status", "")).strip().lower()
    return due < date.today() and status != "paid"


records = fetch_table("payments")
customers = fetch_table("customers")
sales = fetch_table("sales_records")

customer_names = sorted({str(c.get("name", "")).strip() for c in customers if str(c.get("name", "")).strip()})
# Also pull unique party names from sales as additional source
sales_parties = sorted({str(s.get("party_name", "")).strip() for s in sales if str(s.get("party_name", "")).strip()})
all_customer_options = sorted(set(customer_names + sales_parties))

# ── Payment Dues Overview ─────────────────────────────────────────────────────
st.subheader("Payment Dues")
if records:
    df = pd.DataFrame(records)
    df = df.drop(columns=["receipt_document", "created_at"], errors="ignore")
    df = df.rename(columns={
        "customer_name": "Customer Name",
        "invoice_number": "Invoice Number",
        "amount": "Amount",
        "due_date": "Due Date",
        "status": "Status",
    })

    def highlight_overdue(row):
        record = row.to_dict()
        due_str = str(record.get("Due Date", "")).strip()
        status = str(record.get("Status", "")).strip().lower()
        try:
            due = datetime.strptime(due_str, "%Y-%m-%d").date()
            if due < date.today() and status != "paid":
                return ["background-color: #fecaca; color: #7f1d1d;"] * len(row)
        except (TypeError, ValueError):
            pass
        return [""] * len(row)

    display_cols = [c for c in ["Customer Name", "Invoice Number", "Amount", "Due Date", "Status"] if c in df.columns]
    st.dataframe(
        df[display_cols].style.apply(highlight_overdue, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    total_pending = sum(to_float(r.get("amount", 0)) for r in records if str(r.get("status", "")).strip().lower() != "paid")
    st.metric("Total Pending Amount", f"Rs {total_pending:,.2f}")
else:
    st.info("No payment records yet.")

st.markdown("---")

# ── Add Payment ───────────────────────────────────────────────────────────────
st.subheader("Add Payment Record")

# Customer selection outside form for reactivity
cust_options = ["-- Type new --"] + all_customer_options
cust_select = st.selectbox("Customer (choose existing or type new)", options=cust_options, key="pay_cust_select")
cust_new = st.text_input("Or type new customer name (overrides above if filled)", key="pay_cust_new")
prefill_customer = cust_new.strip() if cust_new.strip() else (cust_select if cust_select != "-- Type new --" else "")

# Auto-fill invoice from sales if customer selected
prefill_invoice = ""
if prefill_customer and prefill_customer in all_customer_options:
    matching_sales = [s for s in sales if str(s.get("party_name", "")).strip() == prefill_customer]
    if matching_sales:
        latest = sorted(matching_sales, key=lambda x: str(x.get("date", "")), reverse=True)[0]
        prefill_invoice = str(latest.get("sale_invoice_number", "")).strip()

with st.form("add_payment_form", clear_on_submit=True):
    customer_name = st.text_input("Customer Name", value=prefill_customer)
    invoice_number = st.text_input("Invoice Number", value=prefill_invoice)
    amount = st.number_input("Amount (Rs)", min_value=0.0, step=0.01, value=0.0, format="%.2f")
    due_date = st.date_input("Due Date", value=date.today())
    status = st.selectbox("Status", STATUS_OPTIONS)

    add_submit = st.form_submit_button("Add Payment")
    if add_submit:
        if not customer_name.strip():
            st.error("Customer Name is required.")
        elif not invoice_number.strip():
            st.error("Invoice Number is required.")
        elif amount <= 0:
            st.error("Amount must be greater than 0.")
        else:
            insert_record("payments", {
                "customer_name": customer_name.strip(),
                "invoice_number": invoice_number.strip(),
                "amount": f"{float(amount):.2f}",
                "due_date": due_date.isoformat(),
                "status": status,
            })
            st.success("✅ Payment record added.")
            st.rerun()

st.markdown("---")

# ── Edit / Delete Payment ─────────────────────────────────────────────────────
st.subheader("Edit / Delete Payment")
if not is_admin():
    st.info("🔐 Admin access required.")
elif not records:
    st.info("No payment records to edit.")
else:
    option_map = {}
    for rec in records:
        inv = str(rec.get("invoice_number", "") or "").strip()
        cust = str(rec.get("customer_name", "") or "").strip()
        amt = str(rec.get("amount", "") or "").strip()
        label = f"{cust} | {inv} | Rs {amt}"
        option_map[label] = rec

    selected_key = st.selectbox("Select payment", options=list(option_map.keys()), key="edit_pay_select")
    selected = option_map[selected_key]

    with st.form("edit_payment_form"):
        e_customer = st.text_input("Customer Name", value=str(selected.get("customer_name", "") or ""))
        e_invoice = st.text_input("Invoice Number", value=str(selected.get("invoice_number", "") or ""))
        e_amount = st.number_input("Amount (Rs)", min_value=0.0, step=0.01, value=to_float(selected.get("amount", "0")), format="%.2f")
        e_due = st.date_input("Due Date", value=parse_date(selected.get("due_date", "")))
        current_status = str(selected.get("status", "Pending") or "Pending")
        if current_status not in STATUS_OPTIONS:
            current_status = "Pending"
        e_status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(current_status))

        update_submit = st.form_submit_button("Update Payment")
        if update_submit:
            update_record("payments", {
                "customer_name": e_customer.strip(),
                "invoice_number": e_invoice.strip(),
                "amount": f"{float(e_amount):.2f}",
                "due_date": e_due.isoformat(),
                "status": e_status,
            }, "id", selected.get("id"))
            st.success("✅ Payment updated.")
            st.rerun()

    confirm_delete = st.checkbox("Confirm delete this payment", key="pay_del_confirm")
    if st.button("Delete Payment", type="secondary"):
        if not confirm_delete:
            st.error("Tick the confirm box first.")
        else:
            delete_record("payments", "id", selected.get("id"))
            st.success("Deleted.")
            st.rerun()