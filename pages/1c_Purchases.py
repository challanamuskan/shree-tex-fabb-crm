import base64
import json
from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.constants import (
    PARTS_HEADERS,
    PARTS_TAB,
    PRICE_HISTORY_HEADERS,
    PRICE_HISTORY_TAB,
    PURCHASE_RECORDS_HEADERS,
    PURCHASE_RECORDS_TAB,
)
from utils.sheets_db import append_record, get_or_create_worksheet, read_records, update_record
from utils.ui import get_spreadsheet_connection, init_page

require_login()
init_page("Purchase Records")
st.title("📥 Purchase Records")


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


def files_to_json(uploaded_files):
    data = []
    for f in uploaded_files or []:
        data.append(
            {
                "name": f.name,
                "type": f.type,
                "data": base64.b64encode(f.getvalue()).decode(),
            }
        )
    return json.dumps(data, ensure_ascii=True)


spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

parts_ws = get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS)
purchase_ws = get_or_create_worksheet(spreadsheet, PURCHASE_RECORDS_TAB, PURCHASE_RECORDS_HEADERS)
price_history_ws = get_or_create_worksheet(spreadsheet, PRICE_HISTORY_TAB, PRICE_HISTORY_HEADERS)

parts = read_records(parts_ws, PARTS_HEADERS)
purchases = read_records(purchase_ws, PURCHASE_RECORDS_HEADERS)

part_names = sorted({p.get("Part_Name", "").strip() for p in parts if p.get("Part_Name", "").strip()})

st.subheader("Section A - Record New Purchase")
selection = st.selectbox("Select Part", options=["New Part"] + part_names)

matching_rows = [p for p in parts if p.get("Part_Name", "").strip() == selection]
default_category = matching_rows[0].get("Category", "").strip() if matching_rows else ""
default_sale_price = to_float(matching_rows[0].get("Unit_Sale_Price", "0")) if matching_rows else 0.0
supplier_options = sorted({r.get("Supplier_Name", "").strip() for r in matching_rows if r.get("Supplier_Name", "").strip()})

with st.form("record_purchase_form", clear_on_submit=True):
    if selection == "New Part":
        part_name = st.text_input("Part Name")
        category = st.text_input("Category")
        supplier_name = st.text_input("Supplier Name")
        supplier_phone = st.text_input("Supplier Contact Phone")
        supplier_email = st.text_input("Supplier Contact Email")
        part_number = st.text_input("Part Number")
        reorder_level = st.number_input("Reorder Level", min_value=0, step=1, value=0)
        unit_sale_price = st.number_input("Unit Sale Price", min_value=0.0, step=0.01, value=0.0, format="%.2f")
    else:
        part_name = selection
        category = st.text_input("Category", value=default_category)
        supplier_pick = st.selectbox("Supplier Name", options=supplier_options + ["Other"] if supplier_options else ["Other"])
        supplier_name = st.text_input("Supplier Name (override)", value="" if supplier_pick == "Other" else supplier_pick)
        supplier_phone = st.text_input("Supplier Contact Phone")
        supplier_email = st.text_input("Supplier Contact Email")
        part_number = st.text_input("Part Number", value=matching_rows[0].get("Part_Number", "") if matching_rows else "")
        reorder_level = st.number_input("Reorder Level", min_value=0, step=1, value=to_int(matching_rows[0].get("Reorder_Level", "0")) if matching_rows else 0)
        unit_sale_price = st.number_input("Unit Sale Price", min_value=0.0, step=0.01, value=default_sale_price, format="%.2f")

    qty_purchased = st.number_input("Quantity Purchased", min_value=1, step=1, value=1)
    purchase_invoice = st.text_input("Purchase Invoice Number")
    purchase_price = st.number_input("Purchase Price Per Unit", min_value=0.0, step=0.01, value=0.0, format="%.2f")
    purchase_date = st.date_input("Purchase Date", value=date.today())
    purchase_bills = st.file_uploader(
        "Upload Purchase Bill (optional)",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True,
        key="purchase_bills",
    )

    submit_purchase = st.form_submit_button("Record Purchase")
    if submit_purchase:
        if not part_name.strip() or not category.strip() or not supplier_name.strip() or not purchase_invoice.strip():
            st.error("Part, Category, Supplier and Purchase Invoice Number are required.")
        else:
            target_row = next(
                (
                    p
                    for p in parts
                    if p.get("Part_Name", "").strip().lower() == part_name.strip().lower()
                    and p.get("Supplier_Name", "").strip().lower() == supplier_name.strip().lower()
                ),
                None,
            )

            old_price = to_float(target_row.get("Unit_Purchase_Price", "0")) if target_row else 0.0
            if target_row and abs(old_price - float(purchase_price)) > 1e-9:
                st.info(f"Price changed from ₹{old_price:,.2f} to ₹{float(purchase_price):,.2f} — updating price history")
                append_record(
                    price_history_ws,
                    PRICE_HISTORY_HEADERS,
                    {
                        "Date": purchase_date.isoformat(),
                        "Part_Name": part_name.strip(),
                        "Supplier_Name": supplier_name.strip(),
                        "Old_Price": f"{old_price:.2f}",
                        "New_Price": f"{float(purchase_price):.2f}",
                        "Updated_By": st.session_state.get("username", "system"),
                    },
                )

            if target_row:
                new_qty = to_int(target_row.get("Quantity", "0")) + int(qty_purchased)
                payload = {
                    "Part_Name": part_name.strip(),
                    "Part_Number": part_number.strip(),
                    "Category": category.strip(),
                    "Supplier_Name": supplier_name.strip(),
                    "Supplier_Phone": supplier_phone.strip() or target_row.get("Supplier_Phone", "").strip(),
                    "Supplier_Email": supplier_email.strip() or target_row.get("Supplier_Email", "").strip(),
                    "Quantity": str(new_qty),
                    "Reorder_Level": str(int(reorder_level)),
                    "Unit_Purchase_Price": f"{float(purchase_price):.2f}",
                    "Unit_Sale_Price": f"{float(unit_sale_price):.2f}",
                    "Purchase_Date": purchase_date.isoformat(),
                    "Product_Image": target_row.get("Product_Image", ""),
                    "Part_Documents": target_row.get("Part_Documents", ""),
                }
                update_record(parts_ws, target_row["_row"], PARTS_HEADERS, payload)
            else:
                append_record(
                    parts_ws,
                    PARTS_HEADERS,
                    {
                        "Part_Name": part_name.strip(),
                        "Part_Number": part_number.strip(),
                        "Category": category.strip(),
                        "Supplier_Name": supplier_name.strip(),
                        "Supplier_Phone": supplier_phone.strip(),
                        "Supplier_Email": supplier_email.strip(),
                        "Quantity": str(int(qty_purchased)),
                        "Reorder_Level": str(int(reorder_level)),
                        "Unit_Purchase_Price": f"{float(purchase_price):.2f}",
                        "Unit_Sale_Price": f"{float(unit_sale_price):.2f}",
                        "Purchase_Date": purchase_date.isoformat(),
                        "Product_Image": "",
                        "Part_Documents": "",
                    },
                )

            append_record(
                purchase_ws,
                PURCHASE_RECORDS_HEADERS,
                {
                    "Date": purchase_date.isoformat(),
                    "Part_Name": part_name.strip(),
                    "Category": category.strip(),
                    "Supplier_Name": supplier_name.strip(),
                    "Quantity_Purchased": str(int(qty_purchased)),
                    "Purchase_Invoice_Number": purchase_invoice.strip(),
                    "Purchase_Price_Per_Unit": f"{float(purchase_price):.2f}",
                    "Total_Purchase_Value": f"{float(purchase_price) * int(qty_purchased):.2f}",
                    "Purchase_Bill_Images": files_to_json(purchase_bills),
                },
            )
            st.success("Purchase recorded and stock increased.")
            st.rerun()

st.markdown("---")
st.subheader("Section B - Purchase Records View")
if not purchases:
    st.info("No purchase records found.")
else:
    df = pd.DataFrame(purchases)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    min_date = df["Date"].min().date() if df["Date"].notna().any() else date.today()
    max_date = df["Date"].max().date() if df["Date"].notna().any() else date.today()

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", value=min_date, key="purchase_start")
    with c2:
        end_date = st.date_input("End Date", value=max_date, key="purchase_end")

    supplier_filter = st.selectbox("Supplier", options=["All"] + sorted(df["Supplier_Name"].dropna().astype(str).unique().tolist()))
    part_filter = st.selectbox("Part Name", options=["All"] + sorted(df["Part_Name"].dropna().astype(str).unique().tolist()))

    filtered = df.copy()
    filtered = filtered[(filtered["Date"].dt.date >= start_date) & (filtered["Date"].dt.date <= end_date)]
    if supplier_filter != "All":
        filtered = filtered[filtered["Supplier_Name"].astype(str) == supplier_filter]
    if part_filter != "All":
        filtered = filtered[filtered["Part_Name"].astype(str) == part_filter]

    with st.expander(f"View Purchase Records ({len(filtered)})", expanded=False):
        display_cols = [
            "Date",
            "Part_Name",
            "Supplier_Name",
            "Quantity_Purchased",
            "Purchase_Invoice_Number",
            "Purchase_Price_Per_Unit",
            "Total_Purchase_Value",
            "Purchase_Bill_Images",
        ]
        out = filtered[display_cols].copy()
        out["Date"] = out["Date"].dt.date.astype(str)
        out = out.rename(
            columns={
                "Part_Name": "Part",
                "Supplier_Name": "Supplier",
                "Quantity_Purchased": "Qty",
                "Purchase_Invoice_Number": "Invoice No",
                "Purchase_Price_Per_Unit": "Price/Unit",
                "Total_Purchase_Value": "Total Value",
                "Purchase_Bill_Images": "Bill",
            }
        )
        st.dataframe(out, use_container_width=True, hide_index=True)
