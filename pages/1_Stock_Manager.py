from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import require_login, is_admin
require_login()

from utils.constants import (
    PARTS_HEADERS,
    PARTS_TAB,
    PURCHASE_RECORDS_HEADERS,
    PURCHASE_RECORDS_TAB,
    RETURNS_HEADERS,
    RETURNS_TAB,
    SALES_RECORDS_HEADERS,
    SALES_RECORDS_TAB,
)
from utils.sheets_db import (
    append_record,
    delete_record,
    get_or_create_worksheet,
    read_records,
    update_record,
)
from utils.file_handler import upload_widget, display_document
from utils.ui import (
    get_spreadsheet_connection,
    init_page,
)


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


init_page("Stock Manager")
st.title("Stock Manager")

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

worksheet = get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS)
records = read_records(worksheet, PARTS_HEADERS)
sales_ws = get_or_create_worksheet(spreadsheet, SALES_RECORDS_TAB, SALES_RECORDS_HEADERS)
sales_records = read_records(sales_ws, SALES_RECORDS_HEADERS)
purchase_ws = get_or_create_worksheet(spreadsheet, PURCHASE_RECORDS_TAB, PURCHASE_RECORDS_HEADERS)
purchase_records = read_records(purchase_ws, PURCHASE_RECORDS_HEADERS)
returns_ws = get_or_create_worksheet(spreadsheet, RETURNS_TAB, RETURNS_HEADERS)
return_records = read_records(returns_ws, RETURNS_HEADERS)

def is_low_stock(row):
    return to_int(row.get("Quantity")) < to_int(row.get("Reorder Level"))


def part_option_label(row):
    part_number = row.get("Part Number", "").strip()
    part_name = row.get("Part Name", "").strip() or "Unnamed Part"
    qty = to_int(row.get("Quantity", "0"))
    if part_number:
        return f"{part_number} | {part_name} (Stock: {qty})"
    return f"{part_name} (Stock: {qty})"


st.subheader("Current Stock")
if records:
    display_df = pd.DataFrame(records).drop(columns=["_row", "Product_Image"], errors="ignore")

    def highlight_low_stock(row):
        if to_int(row["Quantity"]) < to_int(row["Reorder Level"]):
            return ["background-color: #ffe4e6"] * len(row)
        return [""] * len(row)

    styled_df = display_df.style.apply(highlight_low_stock, axis=1)
    
    with st.expander(f"📋 View All Stock Records ({len(records)} records) — click to expand", expanded=False):
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    low_stock_count = sum(1 for row in records if is_low_stock(row))
    if low_stock_count:
        st.warning(f"Low stock alert: {low_stock_count} part(s) are below reorder level.")

    parts_with_images = [row for row in records if str(row.get("Product_Image", "")).strip()]
    if parts_with_images:
        st.markdown("#### Product Images")
        for row in parts_with_images:
            part_number = row.get("Part Number", "").strip()
            part_name = row.get("Part Name", "").strip() or "Unnamed Part"
            label = f"{part_number} | {part_name}" if part_number else part_name
            display_document(row.get("Product_Image", ""), label=f"View Image - {label}")
else:
    st.info("No stock records found.")

st.markdown("---")

st.subheader("Sales Record")
if records:
    part_options = {part_option_label(r): r for r in records}
    with st.form("record_sale_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            selected_part_key = st.selectbox("Select Part", options=list(part_options.keys()))
            quantity_sold = st.number_input("Quantity Sold", min_value=1, step=1, value=1)
            sale_invoice_number = st.text_input("Sale Invoice Number")
        with c2:
            party_name = st.text_input("Party Name")
            sale_date = st.date_input("Sale Date", value=date.today())
            sale_price_per_unit = st.number_input(
                "Sale Price per Unit",
                min_value=0.0,
                step=0.01,
                format="%.2f",
            )

        sale_bill_b64 = upload_widget(
            "Sale Bill / Invoice",
            "sale_bill",
            ["jpg", "jpeg", "png", "pdf"],
        )

        record_sale_submit = st.form_submit_button("Record Sale")
        if record_sale_submit:
            selected_part = part_options[selected_part_key]
            available_qty = to_int(selected_part.get("Quantity", "0"))
            sold_qty = int(quantity_sold)

            if not selected_part.get("Part Name", "").strip():
                st.error("Selected part is invalid.")
            elif sold_qty > available_qty:
                st.error(
                    f"Quantity sold ({sold_qty}) exceeds available stock ({available_qty}) for this part."
                )
            else:
                sale_payload = {
                    "Date": sale_date.isoformat(),
                    "Part Name": selected_part.get("Part Name", "").strip(),
                    "Quantity Sold": str(sold_qty),
                    "Sale Invoice Number": sale_invoice_number.strip(),
                    "Party Name": party_name.strip(),
                    "Sale Price Per Unit": f"{float(sale_price_per_unit):.2f}",
                    "Total Sale Value": f"{float(sale_price_per_unit) * sold_qty:.2f}",
                    "Sale_Bill": sale_bill_b64,
                }

                new_qty = available_qty - sold_qty
                stock_payload = {
                    "Part Number": selected_part.get("Part Number", "").strip(),
                    "Part Name": selected_part.get("Part Name", "").strip(),
                    "Category": selected_part.get("Category", "").strip(),
                    "Quantity": str(new_qty),
                    "Reorder Level": str(to_int(selected_part.get("Reorder Level", "0"))),
                    "Unit Price": f"{to_float(selected_part.get('Unit Price', '0')):.2f}",
                    "Supplier Name": selected_part.get("Supplier Name", "").strip(),
                    "Purchase Date": selected_part.get("Purchase Date", "").strip(),
                    "Product_Image": selected_part.get("Product_Image", ""),
                }

                try:
                    append_record(sales_ws, SALES_RECORDS_HEADERS, sale_payload)
                    update_record(worksheet, selected_part["_row"], PARTS_HEADERS, stock_payload)
                    st.success("Sale recorded and stock updated successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error recording sale: {exc}")
else:
    st.info("Add stock items before recording sales.")

st.markdown("---")

st.subheader("Purchase Record")
if records:
    purchase_part_options = {part_option_label(r): r for r in records}
    with st.form("record_purchase_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            purchase_part_key = st.selectbox("Select Part", options=list(purchase_part_options.keys()))
            quantity_purchased = st.number_input("Quantity Purchased", min_value=1, step=1, value=1)
            purchase_invoice_number = st.text_input("Purchase Invoice Number")
        with c2:
            purchase_supplier_name = st.text_input("Supplier Name")
            purchase_price_per_unit = st.number_input(
                "Purchase Price Per Unit",
                min_value=0.0,
                step=0.01,
                format="%.2f",
            )
            purchase_date = st.date_input("Purchase Date", value=date.today())

        purchase_bill_b64 = upload_widget(
            "Purchase Bill / Invoice",
            "purchase_bill",
            ["jpg", "jpeg", "png", "pdf"],
        )

        record_purchase_submit = st.form_submit_button("Record Purchase")
        if record_purchase_submit:
            selected_part = purchase_part_options[purchase_part_key]
            purchased_qty = int(quantity_purchased)
            current_qty = to_int(selected_part.get("Quantity", "0"))
            total_purchase_value = float(purchase_price_per_unit) * purchased_qty

            if not selected_part.get("Part Name", "").strip():
                st.error("Selected part is invalid.")
            else:
                purchase_payload = {
                    "Date": purchase_date.isoformat(),
                    "Part Name": selected_part.get("Part Name", "").strip(),
                    "Quantity Purchased": str(purchased_qty),
                    "Purchase Invoice Number": purchase_invoice_number.strip(),
                    "Supplier Name": purchase_supplier_name.strip(),
                    "Purchase Price Per Unit": f"{float(purchase_price_per_unit):.2f}",
                    "Total Purchase Value": f"{total_purchase_value:.2f}",
                    "Purchase_Bill": purchase_bill_b64,
                }

                updated_stock_payload = {
                    "Part Number": selected_part.get("Part Number", "").strip(),
                    "Part Name": selected_part.get("Part Name", "").strip(),
                    "Category": selected_part.get("Category", "").strip(),
                    "Quantity": str(current_qty + purchased_qty),
                    "Reorder Level": str(to_int(selected_part.get("Reorder Level", "0"))),
                    "Unit Price": f"{to_float(selected_part.get('Unit Price', '0')):.2f}",
                    "Supplier Name": selected_part.get("Supplier Name", "").strip(),
                    "Purchase Date": selected_part.get("Purchase Date", "").strip(),
                    "Product_Image": selected_part.get("Product_Image", ""),
                }

                try:
                    append_record(purchase_ws, PURCHASE_RECORDS_HEADERS, purchase_payload)
                    update_record(worksheet, selected_part["_row"], PARTS_HEADERS, updated_stock_payload)
                    st.success("Purchase recorded and stock updated successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error recording purchase: {exc}")
else:
    st.info("Add stock items before recording purchases.")

st.markdown("---")

st.subheader("Returns")
if records:
    return_part_options = {part_option_label(r): r for r in records}
    sale_return_tab, purchase_return_tab = st.tabs(["Sale Return", "Purchase Return"])

    with sale_return_tab:
        with st.form("sale_return_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                original_sale_invoice_number = st.text_input("Original Sale Invoice Number")
                sale_return_part_key = st.selectbox("Part Name", options=list(return_part_options.keys()))
                sale_return_qty = st.number_input("Quantity Returned", min_value=1, step=1, value=1)
            with c2:
                sale_return_date = st.date_input("Return Date", value=date.today(), key="sale_return_date")
                sale_return_party_name = st.text_input("Party Name")
                sale_return_reason = st.text_input("Reason for Return")

            sale_return_doc_b64 = upload_widget(
                "Return Document",
                "sale_return_doc",
                ["jpg", "jpeg", "png", "pdf"],
            )

            record_sale_return_submit = st.form_submit_button("Record Sale Return")
            if record_sale_return_submit:
                selected_part = return_part_options[sale_return_part_key]
                returned_qty = int(sale_return_qty)
                current_qty = to_int(selected_part.get("Quantity", "0"))

                returns_payload = {
                    "Date": sale_return_date.isoformat(),
                    "Type": "Sale Return",
                    "Part Name": selected_part.get("Part Name", "").strip(),
                    "Quantity": str(returned_qty),
                    "Invoice Number": original_sale_invoice_number.strip(),
                    "Party/Supplier Name": sale_return_party_name.strip(),
                    "Reason": sale_return_reason.strip(),
                    "Return_Document": sale_return_doc_b64,
                }

                updated_stock_payload = {
                    "Part Number": selected_part.get("Part Number", "").strip(),
                    "Part Name": selected_part.get("Part Name", "").strip(),
                    "Category": selected_part.get("Category", "").strip(),
                    "Quantity": str(current_qty + returned_qty),
                    "Reorder Level": str(to_int(selected_part.get("Reorder Level", "0"))),
                    "Unit Price": f"{to_float(selected_part.get('Unit Price', '0')):.2f}",
                    "Supplier Name": selected_part.get("Supplier Name", "").strip(),
                    "Purchase Date": selected_part.get("Purchase Date", "").strip(),
                    "Product_Image": selected_part.get("Product_Image", ""),
                }

                try:
                    append_record(returns_ws, RETURNS_HEADERS, returns_payload)
                    update_record(worksheet, selected_part["_row"], PARTS_HEADERS, updated_stock_payload)
                    st.success("Sale return recorded and stock updated successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error recording sale return: {exc}")

    with purchase_return_tab:
        with st.form("purchase_return_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                original_purchase_invoice_number = st.text_input("Original Purchase Invoice Number")
                purchase_return_part_key = st.selectbox(
                    "Part Name",
                    options=list(return_part_options.keys()),
                    key="purchase_return_part",
                )
                purchase_return_qty = st.number_input(
                    "Quantity Returned",
                    min_value=1,
                    step=1,
                    value=1,
                    key="purchase_return_qty",
                )
            with c2:
                purchase_return_date = st.date_input(
                    "Return Date",
                    value=date.today(),
                    key="purchase_return_date",
                )
                purchase_return_supplier_name = st.text_input("Supplier Name")
                purchase_return_reason = st.text_input("Reason for Return")

            purchase_return_doc_b64 = upload_widget(
                "Return Document",
                "purchase_return_doc",
                ["jpg", "jpeg", "png", "pdf"],
            )

            record_purchase_return_submit = st.form_submit_button("Record Purchase Return")
            if record_purchase_return_submit:
                selected_part = return_part_options[purchase_return_part_key]
                returned_qty = int(purchase_return_qty)
                current_qty = to_int(selected_part.get("Quantity", "0"))

                if returned_qty > current_qty:
                    st.error(
                        f"Quantity returned ({returned_qty}) exceeds available stock ({current_qty}) for this part."
                    )
                else:
                    returns_payload = {
                        "Date": purchase_return_date.isoformat(),
                        "Type": "Purchase Return",
                        "Part Name": selected_part.get("Part Name", "").strip(),
                        "Quantity": str(returned_qty),
                        "Invoice Number": original_purchase_invoice_number.strip(),
                        "Party/Supplier Name": purchase_return_supplier_name.strip(),
                        "Reason": purchase_return_reason.strip(),
                        "Return_Document": purchase_return_doc_b64,
                    }

                    updated_stock_payload = {
                        "Part Number": selected_part.get("Part Number", "").strip(),
                        "Part Name": selected_part.get("Part Name", "").strip(),
                        "Category": selected_part.get("Category", "").strip(),
                        "Quantity": str(current_qty - returned_qty),
                        "Reorder Level": str(to_int(selected_part.get("Reorder Level", "0"))),
                        "Unit Price": f"{to_float(selected_part.get('Unit Price', '0')):.2f}",
                        "Supplier Name": selected_part.get("Supplier Name", "").strip(),
                        "Purchase Date": selected_part.get("Purchase Date", "").strip(),
                        "Product_Image": selected_part.get("Product_Image", ""),
                    }

                    try:
                        append_record(returns_ws, RETURNS_HEADERS, returns_payload)
                        update_record(worksheet, selected_part["_row"], PARTS_HEADERS, updated_stock_payload)
                        st.success("Purchase return recorded and stock updated successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error recording purchase return: {exc}")
else:
    st.info("Add stock items before recording returns.")

st.markdown("---")

st.subheader("Daily Activity Report")
report_date = st.date_input("Select Date", value=date.today(), key="daily_activity_date")
report_date_str = report_date.isoformat()

stock_purchased_rows = [
    r
    for r in purchase_records
    if str(r.get("Date", "")).strip() == report_date_str
]
sales_on_date_rows = [
    r
    for r in sales_records
    if str(r.get("Date", "")).strip() == report_date_str
]
returns_on_date_rows = [
    r
    for r in return_records
    if str(r.get("Date", "")).strip() == report_date_str
]

total_purchased_value = sum(to_float(r.get("Total Purchase Value", "0")) for r in stock_purchased_rows)
total_sales_value = sum(to_float(r.get("Total Sale Value", "0")) for r in sales_on_date_rows)
purchased_qty = sum(to_int(r.get("Quantity Purchased", "0")) for r in stock_purchased_rows)
sales_qty = sum(to_int(r.get("Quantity Sold", "0")) for r in sales_on_date_rows)
sale_return_qty = sum(
    to_int(r.get("Quantity", "0")) for r in returns_on_date_rows if str(r.get("Type", "")).strip() == "Sale Return"
)
purchase_return_qty = sum(
    to_int(r.get("Quantity", "0"))
    for r in returns_on_date_rows
    if str(r.get("Type", "")).strip() == "Purchase Return"
)
net_stock_movement = purchased_qty + sale_return_qty - sales_qty - purchase_return_qty

summary_col1, summary_col2, summary_col3 = st.columns(3)
summary_col1.metric("Total Purchased Value", f"₹{total_purchased_value:,.2f}")
summary_col2.metric("Total Sales Value", f"₹{total_sales_value:,.2f}")
summary_col3.metric("Net Stock Movement", f"{net_stock_movement}")

left_col, middle_col, right_col = st.columns(3)
with left_col:
    st.markdown(f"**Stock Purchased on {report_date_str}**")
    if stock_purchased_rows:
        purchased_df = pd.DataFrame(stock_purchased_rows)
        purchased_display_df = pd.DataFrame(
            {
                "Part Name": purchased_df.get("Part Name", ""),
                "Qty": purchased_df.get("Quantity Purchased", ""),
                "Invoice No": purchased_df.get("Purchase Invoice Number", ""),
                "Supplier": purchased_df.get("Supplier Name", ""),
                "Total Value": purchased_df.get("Total Purchase Value", ""),
            }
        )
        st.dataframe(purchased_display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No purchases recorded on this date.")

with middle_col:
    st.markdown(f"**Sales on {report_date_str}**")
    if sales_on_date_rows:
        sales_df = pd.DataFrame(sales_on_date_rows)
        sales_display_df = pd.DataFrame(
            {
                "Part Name": sales_df.get("Part Name", ""),
                "Qty": sales_df.get("Quantity Sold", ""),
                "Invoice No": sales_df.get("Sale Invoice Number", ""),
                "Party Name": sales_df.get("Party Name", ""),
                "Total Sale Value": sales_df.get("Total Sale Value", ""),
            }
        )
        st.dataframe(sales_display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No sales recorded on this date.")

with right_col:
    st.markdown(f"**Returns on {report_date_str}**")
    if returns_on_date_rows:
        returns_df = pd.DataFrame(returns_on_date_rows)
        returns_display_df = pd.DataFrame(
            {
                "Type": returns_df.get("Type", ""),
                "Part Name": returns_df.get("Part Name", ""),
                "Qty": returns_df.get("Quantity", ""),
                "Invoice No": returns_df.get("Invoice Number", ""),
                "Party/Supplier": returns_df.get("Party/Supplier Name", ""),
            }
        )
        st.dataframe(returns_display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No returns recorded on this date.")

st.markdown("---")

st.subheader("Add Part")
with st.form("add_part_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        part_number = st.text_input("Part Number")
        part_name = st.text_input("Part Name")
        category = st.text_input("Category")
        quantity = st.number_input("Quantity", min_value=0, step=1)
    with c2:
        reorder_level = st.number_input("Reorder Level", min_value=0, step=1)
        unit_price = st.number_input("Unit Price", min_value=0.0, step=0.01, format="%.2f")
        supplier_name = st.text_input("Supplier Name")
        purchase_date = st.date_input("Purchase Date", value=date.today())

    product_image_b64 = upload_widget(
        "Product Image",
        "stock_image",
        ["jpg", "jpeg", "png"],
    )

    add_submit = st.form_submit_button("Add Part")
    if add_submit:
        if not part_name.strip():
            st.error("Part Name is required.")
        else:
            payload = {
                "Part Number": part_number.strip(),
                "Part Name": part_name.strip(),
                "Category": category.strip(),
                "Quantity": str(int(quantity)),
                "Reorder Level": str(int(reorder_level)),
                "Unit Price": f"{float(unit_price):.2f}",
                "Supplier Name": supplier_name.strip(),
                "Purchase Date": purchase_date.isoformat(),
                "Product_Image": product_image_b64,
            }
            try:
                append_record(worksheet, PARTS_HEADERS, payload)
                st.success("Part added successfully.")
                st.rerun()
            except Exception as exc:
                st.error(f"Error adding part: {exc}")

st.markdown("---")
st.subheader("Edit / Delete Part")
if records:
    if is_admin():
        option_map = {
            part_option_label(r): r
            for r in records
        }
        selected_key = st.selectbox("Select part", options=list(option_map.keys()))
        selected = option_map[selected_key]

        with st.form("edit_part_form"):
            c1, c2 = st.columns(2)
            with c1:
                e_part_number = st.text_input("Part Number", value=selected["Part Number"])
                e_part_name = st.text_input("Part Name", value=selected["Part Name"])
                e_category = st.text_input("Category", value=selected["Category"])
                e_quantity = st.number_input(
                    "Quantity",
                    min_value=0,
                    step=1,
                    value=to_int(selected["Quantity"]),
                    key="edit_quantity",
                )
            with c2:
                e_reorder_level = st.number_input(
                    "Reorder Level",
                    min_value=0,
                    step=1,
                    value=to_int(selected["Reorder Level"]),
                    key="edit_reorder",
                )
                e_unit_price = st.number_input(
                    "Unit Price",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f",
                    value=to_float(selected["Unit Price"]),
                    key="edit_price",
                )
                e_supplier_name = st.text_input("Supplier Name", value=selected["Supplier Name"])
                selected_purchase_date = selected.get("Purchase Date", "").strip()
                try:
                    default_purchase_date = date.fromisoformat(selected_purchase_date)
                except ValueError:
                    default_purchase_date = date.today()
                e_purchase_date = st.date_input("Purchase Date", value=default_purchase_date)

            update_submit = st.form_submit_button("Update Part")
            if update_submit:
                if not e_part_name.strip():
                    st.error("Part Name is required.")
                else:
                    payload = {
                        "Part Number": e_part_number.strip(),
                        "Part Name": e_part_name.strip(),
                        "Category": e_category.strip(),
                        "Quantity": str(int(e_quantity)),
                        "Reorder Level": str(int(e_reorder_level)),
                        "Unit Price": f"{float(e_unit_price):.2f}",
                        "Supplier Name": e_supplier_name.strip(),
                        "Purchase Date": e_purchase_date.isoformat(),
                        "Product_Image": selected.get("Product_Image", ""),
                    }
                    try:
                        update_record(worksheet, selected["_row"], PARTS_HEADERS, payload)
                        st.success("Part updated successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error updating part: {exc}")

        confirm_delete = st.checkbox("Confirm delete selected part")
        if st.button("Delete Part", type="secondary"):
            if not confirm_delete:
                st.error("Please confirm deletion first.")
            else:
                try:
                    delete_record(worksheet, selected["_row"])
                    st.success("Part deleted successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error deleting part: {exc}")
    else:
        st.warning("🔐 Admin login required to edit or delete records.")
else:
    st.info("Add a part to enable edit/delete actions.")
