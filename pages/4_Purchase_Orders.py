from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.auth import require_login, is_admin
require_login()

from utils.constants import PURCHASE_ORDERS_HEADERS, PURCHASE_ORDERS_TAB
from utils.sheets_db import (
    append_record,
    delete_record,
    get_or_create_worksheet,
    read_records,
    update_record,
)
from utils.file_handler import upload_and_scan_widget
from utils.ui import (
    get_spreadsheet_connection,
    init_page,
)

STATUS_OPTIONS = ["Ordered", "In Transit", "Delivered", "Cancelled"]


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


init_page("Purchase Orders")
st.title("Purchase Orders")

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

worksheet = get_or_create_worksheet(spreadsheet, PURCHASE_ORDERS_TAB, PURCHASE_ORDERS_HEADERS)
records = read_records(worksheet, PURCHASE_ORDERS_HEADERS)

st.subheader("Orders")
if records:
    df = pd.DataFrame(records).drop(columns=["_row", "Invoice_Document"], errors="ignore")
    display_cols = [
        c
        for c in [
            "Supplier",
            "Invoice Number",
            "Part Name",
            "Quantity Ordered",
            "Unit Price",
            "Line Total",
            "Total Order Value",
            "Order Date",
            "Expected Delivery",
            "Status",
        ]
        if c in df.columns
    ]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
else:
    st.info("No purchase orders found.")

st.markdown("---")
st.subheader("Create Purchase Order")
if "po_product_count" not in st.session_state:
    st.session_state["po_product_count"] = 1

bill_b64, scan_data = upload_and_scan_widget("Supplier Invoice", "po_invoice")
scanned_order_date = parse_scanned_date(scan_data.get("date", ""))
scanned_qty = max(1, to_int(scan_data.get("quantity", "1")))

header_c1, header_c2 = st.columns(2)
with header_c1:
    supplier = st.text_input("Supplier Name", value=scan_data.get("party_name", ""), key="po_supplier")
    invoice_number = st.text_input("Invoice Number", value=scan_data.get("invoice_number", ""), key="po_invoice_number")
with header_c2:
    order_date = st.date_input("Order Date", value=scanned_order_date, key="po_order_date")
    expected_delivery = st.date_input(
        "Expected Delivery",
        value=date.today(),
        key="po_expected_delivery",
    )

status = st.selectbox("Status", STATUS_OPTIONS, key="po_status")

if st.button("Add Another Product"):
    st.session_state["po_product_count"] += 1

product_rows = []
for idx in range(st.session_state["po_product_count"]):
    st.markdown(f"**Product {idx + 1}**")
    p1, p2, p3 = st.columns([2, 1, 1])
    with p1:
        p_name = st.text_input("Part Name", key=f"po_part_name_{idx}")
    with p2:
        p_qty = st.number_input("Quantity", min_value=1, step=1, value=scanned_qty, key=f"po_qty_{idx}")
    with p3:
        p_unit_price = st.number_input(
            "Unit Price",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            key=f"po_unit_price_{idx}",
        )
    line_total = int(p_qty) * float(p_unit_price)
    st.caption(f"Line Total: Rs {line_total:,.2f}")
    product_rows.append(
        {
            "Part Name": p_name.strip(),
            "Quantity Ordered": int(p_qty),
            "Unit Price": float(p_unit_price),
            "Line Total": line_total,
        }
    )

valid_products = [p for p in product_rows if p["Part Name"]]
total_order_value = sum(p["Line Total"] for p in valid_products)

st.markdown("**Order Summary**")
summary_df = pd.DataFrame(valid_products)
if not summary_df.empty:
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
else:
    st.info("Add at least one product name to build order summary.")
st.markdown(f"**Total Order Value: Rs {total_order_value:,.2f}**")

if st.button("Create Order"):
    if not supplier.strip() or not invoice_number.strip():
        st.error("Supplier Name and Invoice Number are required.")
    elif not valid_products:
        st.error("Add at least one valid product row.")
    else:
        try:
            for item in valid_products:
                payload = {
                    "Supplier": supplier.strip(),
                    "Invoice Number": invoice_number.strip(),
                    "Part Name": item["Part Name"],
                    "Quantity Ordered": str(item["Quantity Ordered"]),
                    "Unit Price": f"{item['Unit Price']:.2f}",
                    "Line Total": f"{item['Line Total']:.2f}",
                    "Total Order Value": f"{total_order_value:.2f}",
                    "Order Date": order_date.isoformat(),
                    "Expected Delivery": expected_delivery.isoformat(),
                    "Status": status,
                    "Invoice_Document": bill_b64,
                }
                append_record(worksheet, PURCHASE_ORDERS_HEADERS, payload)
            st.success("Purchase order created successfully.")
            st.session_state["po_product_count"] = 1
            st.rerun()
        except Exception as exc:
            st.error(f"Error creating purchase order: {exc}")

st.markdown("---")
st.subheader("Edit / Delete Purchase Order")
if records:
    if is_admin():
        option_map = {
            f"{r.get('Supplier', '').strip()} | {r.get('Invoice Number', '').strip() or 'No Invoice'} | {r.get('Part Name', '').strip()}": r
            for r in records
        }
        selected_key = st.selectbox("Select order", options=list(option_map.keys()))
        selected = option_map[selected_key]

        with st.form("edit_po_form"):
            c1, c2 = st.columns(2)
            with c1:
                e_supplier = st.text_input("Supplier", value=selected["Supplier"])
                e_invoice_number = st.text_input("Invoice Number", value=selected.get("Invoice Number", ""))
                e_part_name = st.text_input("Part Name", value=selected["Part Name"])
                e_quantity = st.number_input(
                    "Quantity Ordered",
                    min_value=1,
                    step=1,
                    value=max(1, to_int(selected["Quantity Ordered"])),
                )
            with c2:
                e_unit_price = st.number_input(
                    "Unit Price",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    value=to_float(selected.get("Unit Price", "0")),
                )
                e_order_date = st.date_input("Order Date", value=parse_date(selected["Order Date"]))
                e_expected_delivery = st.date_input(
                    "Expected Delivery",
                    value=parse_date(selected["Expected Delivery"]),
                )
                current_status = selected["Status"] if selected["Status"] in STATUS_OPTIONS else STATUS_OPTIONS[0]
                e_status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(current_status))

            update_submit = st.form_submit_button("Update Order")
            if update_submit:
                if not e_supplier.strip() or not e_part_name.strip():
                    st.error("Supplier and Part Name are required.")
                else:
                    e_line_total = int(e_quantity) * float(e_unit_price)
                    payload = {
                        "Supplier": e_supplier.strip(),
                        "Invoice Number": e_invoice_number.strip(),
                        "Part Name": e_part_name.strip(),
                        "Quantity Ordered": str(int(e_quantity)),
                        "Unit Price": f"{float(e_unit_price):.2f}",
                        "Line Total": f"{e_line_total:.2f}",
                        "Total Order Value": selected.get("Total Order Value", f"{e_line_total:.2f}"),
                        "Order Date": e_order_date.isoformat(),
                        "Expected Delivery": e_expected_delivery.isoformat(),
                        "Status": e_status,
                        "Invoice_Document": selected.get("Invoice_Document", ""),
                    }
                    try:
                        update_record(worksheet, selected["_row"], PURCHASE_ORDERS_HEADERS, payload)
                        st.success("Purchase order updated successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error updating purchase order: {exc}")

        confirm_delete = st.checkbox("Confirm delete selected order")
        if st.button("Delete Order", type="secondary"):
            if not confirm_delete:
                st.error("Please confirm deletion first.")
            else:
                try:
                    delete_record(worksheet, selected["_row"])
                    st.success("Purchase order deleted successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error deleting purchase order: {exc}")
    else:
        st.warning("🔐 Admin login required to edit or delete records.")
else:
    st.info("Create an order to enable edit/delete actions.")
