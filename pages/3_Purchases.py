import base64
import json
from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.supabase_db import delete_record, fetch_table, insert_record, update_record
from utils.ui import init_page

require_login()
init_page("Purchase Records")
st.title("Purchase Records")


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
purchases = fetch_table("purchase_records")

category_names = sorted({str(c.get("category_name", "")).strip() for c in categories if str(c.get("category_name", "")).strip()})
if not category_names:
    category_names = sorted({str(p.get("category", "")).strip() or "uncategorised" for p in parts})

st.subheader("Record New Purchase")
purchase_mode = st.radio("Purchase mode", ["Existing Part", "New Part"], horizontal=True)

if purchase_mode == "Existing Part":
    selected_category = st.selectbox("Select Category", options=category_names, key="purchase_category")
    category_rows = [p for p in parts if (str(p.get("category", "")).strip() or "uncategorised") == selected_category]
    part_names = sorted({str(p.get("part_name", "")).strip() for p in category_rows if str(p.get("part_name", "")).strip()})
    if not part_names:
        st.info("No parts found in the selected category.")
        st.stop()
    selection = st.selectbox("Select Part", options=part_names, key="purchase_part")
    matching_rows = [p for p in category_rows if str(p.get("part_name", "")).strip() == selection]
    default_category = selected_category
    default_sale_price = to_float(matching_rows[0].get("unit_sale_price", "0")) if matching_rows else 0.0
    supplier_options = sorted({str(r.get("supplier_name", "")).strip() for r in matching_rows if str(r.get("supplier_name", "")).strip()})
else:
    selection = "New Part"
    matching_rows = []
    default_category = ""
    default_sale_price = 0.0
    supplier_options = []

with st.form("record_purchase_form", clear_on_submit=True):
    if purchase_mode == "New Part":
        part_name = st.text_input("Part Name")
        category = st.text_input("Category")
        supplier_name = st.text_input("Supplier Name")
        unit_sale_price = st.number_input("Unit Sale Price", min_value=0.0, step=0.01, value=0.0, format="%.2f")
    else:
        part_name = selection
        category = st.text_input("Category", value=default_category)
        supplier_pick = st.selectbox("Supplier Name", options=supplier_options + ["Other"] if supplier_options else ["Other"])
        supplier_name = st.text_input("Supplier Name (override)", value="" if supplier_pick == "Other" else supplier_pick)
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
                    if str(p.get("part_name", "")).strip().lower() == part_name.strip().lower()
                    and str(p.get("supplier_name", "")).strip().lower() == supplier_name.strip().lower()
                ),
                None,
            )

            old_price = to_float(target_row.get("unit_sale_price", "0")) if target_row else 0.0
            if target_row and abs(old_price - float(purchase_price)) > 1e-9:
                insert_record(
                    "price_history",
                    {
                        "date": purchase_date.isoformat(),
                        "part_name": part_name.strip(),
                        "supplier_name": supplier_name.strip(),
                        "old_price": f"{old_price:.2f}",
                        "new_price": f"{float(purchase_price):.2f}",
                        "updated_by": st.session_state.get("username", "system"),
                    },
                )

            if target_row:
                new_qty = to_int(target_row.get("quantity", "0")) + int(qty_purchased)
                payload = {
                    "cid": str(target_row.get("cid", "") or ""),
                    "part_name": part_name.strip(),
                    "category": category.strip(),
                    "unit_sale_price": f"{float(unit_sale_price):.2f}",
                    "quantity": str(new_qty),
                    "status": str(target_row.get("status", "") or ""),
                    "date_added": str(target_row.get("date_added", "") or purchase_date.isoformat()),
                    "legacy_id": str(target_row.get("legacy_id", "") or ""),
                    "price_type": str(target_row.get("price_type", "") or ""),
                    "box_number": str(target_row.get("box_number", "") or ""),
                    "supplier_name": supplier_name.strip(),
                    "image": str(target_row.get("image", "") or ""),
                }
                update_record("parts", payload, "id", target_row.get("id"))
            else:
                insert_record(
                    "parts",
                    {
                        "cid": "",
                        "category": category.strip(),
                        "part_name": part_name.strip(),
                        "unit_sale_price": f"{float(unit_sale_price):.2f}",
                        "quantity": str(int(qty_purchased)),
                        "status": "",
                        "date_added": purchase_date.isoformat(),
                        "legacy_id": "",
                        "price_type": "",
                        "box_number": "",
                        "supplier_name": supplier_name.strip(),
                        "image": "",
                    },
                )

            insert_record(
                "purchase_records",
                {
                    "date": purchase_date.isoformat(),
                    "part_name": part_name.strip(),
                    "category": category.strip(),
                    "supplier_name": supplier_name.strip(),
                    "quantity_purchased": str(int(qty_purchased)),
                    "purchase_invoice_number": purchase_invoice.strip(),
                    "purchase_price_per_unit": f"{float(purchase_price):.2f}",
                    "total_purchase_value": f"{float(purchase_price) * int(qty_purchased):.2f}",
                    "purchase_bill_images": files_to_json(purchase_bills),
                },
            )
            st.success("Purchase recorded and stock increased.")
            st.rerun()

st.markdown("---")
st.subheader("Purchase Records View")
if not purchases:
    st.info("No purchase records found.")
else:
    df = pd.DataFrame(purchases)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    min_date = df["date"].min().date() if ("date" in df.columns and df["date"].notna().any()) else date.today()
    max_date = df["date"].max().date() if ("date" in df.columns and df["date"].notna().any()) else date.today()

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", value=min_date, key="purchase_start")
    with c2:
        end_date = st.date_input("End Date", value=max_date, key="purchase_end")

    filter_categories = sorted(df["category"].dropna().astype(str).replace("", "uncategorised").unique().tolist()) if "category" in df.columns else []
    supplier_values = sorted(df["supplier_name"].dropna().astype(str).unique().tolist()) if "supplier_name" in df.columns else []
    supplier_filter = st.selectbox("Supplier", options=["All"] + supplier_values)
    part_filter_category = st.selectbox("Category", options=["All"] + filter_categories)

    filtered_parts = df.copy()
    if part_filter_category != "All" and "category" in filtered_parts.columns:
        filtered_parts = filtered_parts[filtered_parts["category"].astype(str).replace("", "uncategorised") == part_filter_category]

    part_names = sorted(filtered_parts["part_name"].dropna().astype(str).unique().tolist()) if "part_name" in filtered_parts.columns else []
    part_filter = st.selectbox("Part Name", options=["All"] + part_names)

    filtered = df.copy()
    if "date" in filtered.columns:
        filtered = filtered[(filtered["date"].dt.date >= start_date) & (filtered["date"].dt.date <= end_date)]
    if supplier_filter != "All" and "supplier_name" in filtered.columns:
        filtered = filtered[filtered["supplier_name"].astype(str) == supplier_filter]
    if part_filter_category != "All" and "category" in filtered.columns:
        filtered = filtered[filtered["category"].astype(str).replace("", "uncategorised") == part_filter_category]
    if part_filter != "All" and "part_name" in filtered.columns:
        filtered = filtered[filtered["part_name"].astype(str) == part_filter]

    with st.expander(f"View Purchase Records ({len(filtered)})", expanded=False):
        display_cols = [
            "date",
            "part_name",
            "supplier_name",
            "quantity_purchased",
            "purchase_invoice_number",
            "purchase_price_per_unit",
            "total_purchase_value",
            "purchase_bill_images",
        ]
        existing = [c for c in display_cols if c in filtered.columns]
        out = filtered[existing].copy()
        if "date" in out.columns:
            out["date"] = out["date"].dt.date.astype(str)
        st.dataframe(out, use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("Edit / Delete Purchase")
if not purchases:
    st.info("No purchase records available.")
else:
    option_map = {}
    for rec in purchases:
        label = f"{rec.get('purchase_invoice_number', '')} | {rec.get('date', '')} | {rec.get('part_name', '')}"
        option_map[label] = rec

    selected_key = st.selectbox("Select purchase record", options=list(option_map.keys()))
    selected = option_map[selected_key]

    with st.form("edit_purchase_form"):
        e_date = st.date_input("Date", value=pd.to_datetime(selected.get("date", date.today()), errors="coerce").date())
        e_part = st.text_input("Part Name", value=str(selected.get("part_name", "")))
        e_category = st.text_input("Category", value=str(selected.get("category", "")))
        e_supplier = st.text_input("Supplier Name", value=str(selected.get("supplier_name", "")))
        e_qty = st.number_input("Quantity Purchased", min_value=1, step=1, value=max(1, to_int(selected.get("quantity_purchased", "1"))))
        e_invoice = st.text_input("Purchase Invoice Number", value=str(selected.get("purchase_invoice_number", "")))
        e_price = st.number_input("Purchase Price Per Unit", min_value=0.0, step=0.01, value=to_float(selected.get("purchase_price_per_unit", "0")), format="%.2f")

        update_submit = st.form_submit_button("Update Purchase")
        if update_submit:
            payload = {
                "date": e_date.isoformat(),
                "part_name": e_part.strip(),
                "category": e_category.strip(),
                "supplier_name": e_supplier.strip(),
                "quantity_purchased": str(int(e_qty)),
                "purchase_invoice_number": e_invoice.strip(),
                "purchase_price_per_unit": f"{float(e_price):.2f}",
                "total_purchase_value": f"{float(e_price) * int(e_qty):.2f}",
            }
            update_record("purchase_records", payload, "id", selected.get("id"))
            st.success("Purchase record updated.")
            st.rerun()

    confirm_delete = st.checkbox("Confirm delete selected purchase", key="purchase_delete_confirm")
    if st.button("Delete Purchase", type="secondary"):
        if not confirm_delete:
            st.error("Please confirm deletion first.")
        else:
            delete_record("purchase_records", "id", selected.get("id"))
            st.success("Purchase record deleted.")
            st.rerun()
