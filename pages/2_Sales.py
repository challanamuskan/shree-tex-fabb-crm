import base64
import json
from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.supabase_db import delete_record, fetch_table, insert_record, update_record
from utils.ui import init_page

require_login()
init_page("Sales Records")
st.title("Sales Records")


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


parts = fetch_table("parts")
categories = fetch_table("categories")
sales = fetch_table("sales_records")

category_names = sorted({str(c.get("category_name", "")).strip() for c in categories if str(c.get("category_name", "")).strip()})
if not category_names:
    category_names = sorted({str(p.get("category", "")).strip() or "uncategorised" for p in parts})

st.subheader("Record New Sale")
if not parts:
    st.info("No parts found in stock.")
else:
    with st.form("record_sale_form", clear_on_submit=True):
        selected_category = st.selectbox("Select Category", options=category_names, key="sale_category")
        category_rows = [p for p in parts if (str(p.get("category", "")).strip() or "uncategorised") == selected_category]
        part_names = sorted({str(p.get("part_name", "")).strip() for p in category_rows if str(p.get("part_name", "")).strip()})

        if not part_names:
            st.info("No parts found in the selected category.")
            st.form_submit_button("Record Sale", disabled=True)
        else:
            selected_part = st.selectbox("Select Part", options=part_names, key="sale_part")
            matching_rows = [p for p in category_rows if str(p.get("part_name", "")).strip() == selected_part]
            total_stock = sum(to_int(r.get("quantity", "0")) for r in matching_rows)
            st.caption(f"Available stock: {total_stock}")

            supplier_options = sorted({str(r.get("supplier_name", "")).strip() for r in matching_rows if str(r.get("supplier_name", "")).strip()})
            supplier_choice = st.selectbox("Supplier", options=["Any"] + supplier_options)

            qty_sold = st.number_input("Quantity Sold", min_value=1, step=1, value=1)
            sale_invoice = st.text_input("Sale Invoice Number")
            party_name = st.text_input("Party Name")
            sale_date = st.date_input("Sale Date", value=date.today())
            default_sale_price = to_float(matching_rows[0].get("unit_sale_price", "0")) if matching_rows else 0.0
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
                    rows_scope = matching_rows if supplier_choice == "Any" else [r for r in matching_rows if str(r.get("supplier_name", "")).strip() == supplier_choice]
                    rows_scope = sorted(rows_scope, key=lambda r: to_int(r.get("quantity", "0")), reverse=True)

                    rows_to_update = []
                    for row in rows_scope:
                        if remaining <= 0:
                            break
                        available = to_int(row.get("quantity", "0"))
                        take = min(available, remaining)
                        if take <= 0:
                            continue
                        remaining -= take
                        rows_to_update.append((row, available - take))

                    if remaining > 0:
                        st.error("Not enough stock in selected supplier scope.")
                    else:
                        for row, new_qty in rows_to_update:
                            update_record("parts", {"quantity": str(new_qty)}, "id", row.get("id"))

                        insert_record(
                            "sales_records",
                            {
                                "date": sale_date.isoformat(),
                                "part_name": selected_part,
                                "category": selected_category,
                                "supplier": supplier_choice,
                                "quantity_sold": str(int(qty_sold)),
                                "sale_invoice_number": sale_invoice.strip(),
                                "party_name": party_name.strip(),
                                "sale_price_per_unit": f"{float(sale_price):.2f}",
                                "total_sale_value": f"{float(sale_price) * int(qty_sold):.2f}",
                                "sale_bill_images": files_to_json(sale_bills),
                            },
                        )
                        st.success("Sale recorded and stock updated.")
                        st.rerun()

st.markdown("---")
st.subheader("Sales Records View")
if not sales:
    st.info("No sales records found.")
else:
    df = pd.DataFrame(sales)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    min_date = df["date"].min().date() if ("date" in df.columns and df["date"].notna().any()) else date.today()
    max_date = df["date"].max().date() if ("date" in df.columns and df["date"].notna().any()) else date.today()

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", value=min_date, key="sales_start")
    with c2:
        end_date = st.date_input("End Date", value=max_date, key="sales_end")

    filter_categories = sorted(df["category"].dropna().astype(str).replace("", "uncategorised").unique().tolist()) if "category" in df.columns else []
    part_filter_category = st.selectbox("Category", options=["All"] + filter_categories)

    filtered_parts = df.copy()
    if part_filter_category != "All" and "category" in filtered_parts.columns:
        filtered_parts = filtered_parts[filtered_parts["category"].astype(str).replace("", "uncategorised") == part_filter_category]

    part_names = sorted(filtered_parts["part_name"].dropna().astype(str).unique().tolist()) if "part_name" in filtered_parts.columns else []
    part_filter = st.selectbox("Part Name", options=["All"] + part_names)
    party_filter = st.text_input("Party Name contains")

    filtered = df.copy()
    if "date" in filtered.columns:
        filtered = filtered[(filtered["date"].dt.date >= start_date) & (filtered["date"].dt.date <= end_date)]
    if part_filter_category != "All" and "category" in filtered.columns:
        filtered = filtered[filtered["category"].astype(str).replace("", "uncategorised") == part_filter_category]
    if part_filter != "All" and "part_name" in filtered.columns:
        filtered = filtered[filtered["part_name"].astype(str) == part_filter]
    if party_filter.strip() and "party_name" in filtered.columns:
        filtered = filtered[filtered["party_name"].astype(str).str.contains(party_filter.strip(), case=False, na=False)]

    total_sales_value = pd.to_numeric(filtered.get("total_sale_value", 0), errors="coerce").fillna(0).sum()
    st.markdown(f"Total sales value for filtered period: Rs {total_sales_value:,.2f}")

    with st.expander(f"View Sales Records ({len(filtered)})", expanded=False):
        display_cols = [
            "date",
            "part_name",
            "category",
            "quantity_sold",
            "sale_invoice_number",
            "party_name",
            "sale_price_per_unit",
            "total_sale_value",
            "sale_bill_images",
        ]
        existing = [c for c in display_cols if c in filtered.columns]
        out = filtered[existing].copy()
        if "date" in out.columns:
            out["date"] = out["date"].dt.date.astype(str)
        st.dataframe(out, use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("Edit / Delete Sale")
if not sales:
    st.info("No sales records available.")
else:
    option_map = {}
    for rec in sales:
        label = f"{rec.get('sale_invoice_number', '')} | {rec.get('date', '')} | {rec.get('part_name', '')}"
        option_map[label] = rec

    selected_key = st.selectbox("Select sale record", options=list(option_map.keys()))
    selected = option_map[selected_key]

    with st.form("edit_sale_form"):
        e_date = st.date_input("Date", value=pd.to_datetime(selected.get("date", date.today()), errors="coerce").date())
        e_part = st.text_input("Part Name", value=str(selected.get("part_name", "")))
        e_category = st.text_input("Category", value=str(selected.get("category", "")))
        e_supplier = st.text_input("Supplier", value=str(selected.get("supplier", "")))
        e_qty = st.number_input("Quantity Sold", min_value=1, step=1, value=max(1, to_int(selected.get("quantity_sold", "1"))))
        e_invoice = st.text_input("Invoice Number", value=str(selected.get("sale_invoice_number", "")))
        e_party = st.text_input("Party Name", value=str(selected.get("party_name", "")))
        e_price = st.number_input("Sale Price Per Unit", min_value=0.0, step=0.01, value=to_float(selected.get("sale_price_per_unit", "0")), format="%.2f")

        update_submit = st.form_submit_button("Update Sale")
        if update_submit:
            payload = {
                "date": e_date.isoformat(),
                "part_name": e_part.strip(),
                "category": e_category.strip(),
                "supplier": e_supplier.strip(),
                "quantity_sold": str(int(e_qty)),
                "sale_invoice_number": e_invoice.strip(),
                "party_name": e_party.strip(),
                "sale_price_per_unit": f"{float(e_price):.2f}",
                "total_sale_value": f"{float(e_price) * int(e_qty):.2f}",
            }
            update_record("sales_records", payload, "id", selected.get("id"))
            st.success("Sale record updated.")
            st.rerun()

    confirm_delete = st.checkbox("Confirm delete selected sale", key="sale_delete_confirm")
    if st.button("Delete Sale", type="secondary"):
        if not confirm_delete:
            st.error("Please confirm deletion first.")
        else:
            delete_record("sales_records", "id", selected.get("id"))
            st.success("Sale record deleted.")
            st.rerun()
