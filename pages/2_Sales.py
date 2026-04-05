import base64
import json
from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.constants import CATEGORIES_HEADERS, CATEGORIES_TAB, PARTS_HEADERS, PARTS_TAB, SALES_RECORDS_HEADERS, SALES_RECORDS_TAB
from utils.sheets_db import append_record, fetch_sheet_data_by_name, get_or_create_worksheet, update_record
from utils.ui import get_spreadsheet_connection, init_page

require_login()
init_page("Sales Records")
st.title("💰 Sales Records")


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

parts = fetch_sheet_data_by_name(PARTS_TAB, PARTS_HEADERS)
categories = fetch_sheet_data_by_name(CATEGORIES_TAB, CATEGORIES_HEADERS)
sales = fetch_sheet_data_by_name(SALES_RECORDS_TAB, SALES_RECORDS_HEADERS)
category_names = sorted({p.get("Category_Name", "").strip() for p in categories if p.get("Category_Name", "").strip()})
if not category_names:
    category_names = sorted({p.get("Category", "").strip() or "Uncategorised" for p in parts})

st.subheader("Section A - Record New Sale")
if not parts:
    st.info("No parts found in stock.")
else:
    with st.form("record_sale_form", clear_on_submit=True):
        selected_category = st.selectbox("Select Category", options=category_names, key="sale_category")
        category_rows = [p for p in parts if (p.get("Category", "").strip() or "Uncategorised") == selected_category]
        part_names = sorted({p.get("Part_Name", "").strip() for p in category_rows if p.get("Part_Name", "").strip()})
        if not part_names:
            st.info("No parts found in the selected category.")
            st.form_submit_button("Record Sale", disabled=True)
        else:
            selected_part = st.selectbox("Select Part", options=part_names, key="sale_part")

            matching_rows = [p for p in category_rows if p.get("Part_Name", "").strip() == selected_part]
            total_stock = sum(to_int(r.get("Quantity", "0")) for r in matching_rows)
            st.caption(f"Available stock: {total_stock}")

            supplier_options = sorted({r.get("Supplier_Name", "").strip() for r in matching_rows if r.get("Supplier_Name", "").strip()})
            supplier_choice = st.selectbox("Supplier", options=["Any"] + supplier_options)

            qty_sold = st.number_input("Quantity Sold", min_value=1, step=1, value=1)
            sale_invoice = st.text_input("Sale Invoice Number")
            party_name = st.text_input("Party Name")
            sale_date = st.date_input("Sale Date", value=date.today())
            default_sale_price = to_float(matching_rows[0].get("Unit_Sale_Price", "0")) if matching_rows else 0.0
            sale_price = st.number_input("Sale Price Per Unit", min_value=0.0, step=0.01, value=default_sale_price, format="%.2f")
            sale_bills = st.file_uploader(
                "Upload Sale Bill (optional)",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True,
                key="sale_bills",
            )

            submit_button = st.form_submit_button("Record Sale")
            if submit_button:
                if qty_sold > total_stock:
                    st.error(f"Quantity sold exceeds available stock ({total_stock}).")
                elif not sale_invoice.strip() or not party_name.strip():
                    st.error("Sale Invoice Number and Party Name are required.")
                else:
                    remaining = int(qty_sold)
                    rows_to_update = []
                    rows_scope = matching_rows if supplier_choice == "Any" else [r for r in matching_rows if r.get("Supplier_Name", "").strip() == supplier_choice]
                    rows_scope = sorted(rows_scope, key=lambda r: to_int(r.get("Quantity", "0")), reverse=True)

                    for row in rows_scope:
                        if remaining <= 0:
                            break
                        available = to_int(row.get("Quantity", "0"))
                        take = min(available, remaining)
                        if take <= 0:
                            continue
                        remaining -= take
                        rows_to_update.append((row, available - take))

                    if remaining > 0:
                        st.error("Not enough stock in selected supplier scope.")
                    else:
                        for row, new_qty in rows_to_update:
                            payload = {
                                "Part_Name": row.get("Part_Name", "").strip(),
                                "Part_Number": row.get("Part_Number", "").strip(),
                                "Category": row.get("Category", "").strip(),
                                "Supplier_Name": row.get("Supplier_Name", "").strip(),
                                "Supplier_Phone": row.get("Supplier_Phone", "").strip(),
                                "Supplier_Email": row.get("Supplier_Email", "").strip(),
                                "Quantity": str(new_qty),
                                "Reorder_Level": str(to_int(row.get("Reorder_Level", "0"))),
                                "Unit_Purchase_Price": f"{to_float(row.get('Unit_Purchase_Price', '0')):.2f}",
                                "Unit_Sale_Price": f"{to_float(row.get('Unit_Sale_Price', '0')):.2f}",
                                "Purchase_Date": row.get("Purchase_Date", "").strip(),
                                "Product_Image": row.get("Product_Image", ""),
                                "Part_Documents": row.get("Part_Documents", ""),
                            }
                            update_record(
                                get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS),
                                row["_row"],
                                PARTS_HEADERS,
                                payload,
                            )

                        append_record(
                            get_or_create_worksheet(spreadsheet, SALES_RECORDS_TAB, SALES_RECORDS_HEADERS),
                            SALES_RECORDS_HEADERS,
                            {
                                "Date": sale_date.isoformat(),
                                "Part_Name": selected_part,
                                "Category": selected_category,
                                "Supplier": supplier_choice,
                                "Quantity_Sold": str(int(qty_sold)),
                                "Sale_Invoice_Number": sale_invoice.strip(),
                                "Party_Name": party_name.strip(),
                                "Sale_Price_Per_Unit": f"{float(sale_price):.2f}",
                                "Total_Sale_Value": f"{float(sale_price) * int(qty_sold):.2f}",
                                "Sale_Bill_Images": files_to_json(sale_bills),
                            },
                        )
                        st.success("Sale recorded and stock updated.")
                        st.rerun()

st.markdown("---")
st.subheader("Section B - Sales Records View")
if not sales:
    st.info("No sales records found.")
else:
    df = pd.DataFrame(sales)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    min_date = df["Date"].min().date() if df["Date"].notna().any() else date.today()
    max_date = df["Date"].max().date() if df["Date"].notna().any() else date.today()

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", value=min_date, key="sales_start")
    with c2:
        end_date = st.date_input("End Date", value=max_date, key="sales_end")

    filter_categories = sorted(df["Category"].dropna().astype(str).replace("", "Uncategorised").unique().tolist())
    part_filter_category = st.selectbox("Category", options=["All"] + filter_categories)
    filtered_parts = df.copy()
    if part_filter_category != "All":
        filtered_parts = filtered_parts[filtered_parts["Category"].astype(str).replace("", "Uncategorised") == part_filter_category]
    part_filter = st.selectbox("Part Name", options=["All"] + sorted(filtered_parts["Part_Name"].dropna().astype(str).unique().tolist()))
    party_filter = st.text_input("Party Name contains")

    filtered = df.copy()
    filtered = filtered[(filtered["Date"].dt.date >= start_date) & (filtered["Date"].dt.date <= end_date)]
    if part_filter_category != "All":
        filtered = filtered[filtered["Category"].astype(str).replace("", "Uncategorised") == part_filter_category]
    if part_filter != "All":
        filtered = filtered[filtered["Part_Name"].astype(str) == part_filter]
    if party_filter.strip():
        filtered = filtered[filtered["Party_Name"].astype(str).str.contains(party_filter.strip(), case=False, na=False)]

    total_sales_value = pd.to_numeric(filtered.get("Total_Sale_Value", 0), errors="coerce").fillna(0).sum()
    st.markdown(f"Total sales value for filtered period: ₹{total_sales_value:,.2f}")

    with st.expander(f"View Sales Records ({len(filtered)})", expanded=False):
        display_cols = [
            "Date",
            "Part_Name",
            "Category",
            "Quantity_Sold",
            "Sale_Invoice_Number",
            "Party_Name",
            "Sale_Price_Per_Unit",
            "Total_Sale_Value",
            "Sale_Bill_Images",
        ]
        out = filtered[display_cols].copy()
        out["Date"] = out["Date"].dt.date.astype(str)
        out = out.rename(
            columns={
                "Part_Name": "Part",
                "Quantity_Sold": "Qty",
                "Sale_Invoice_Number": "Invoice No",
                "Party_Name": "Party",
                "Sale_Price_Per_Unit": "Price/Unit",
                "Total_Sale_Value": "Total Value",
                "Sale_Bill_Images": "Bill",
            }
        )
        st.dataframe(out, use_container_width=True, hide_index=True)
