import base64
import json
from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import require_login, is_admin
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
        data.append({
            "name": f.name,
            "type": f.type,
            "data": base64.b64encode(f.getvalue()).decode(),
        })
    return json.dumps(data, ensure_ascii=True)


parts = fetch_table("parts")
categories = fetch_table("categories")
purchases = fetch_table("purchase_records")
customers = fetch_table("customers")

category_names = sorted({str(c.get("category_name", "")).strip() for c in categories if str(c.get("category_name", "")).strip()})
if not category_names:
    category_names = sorted({str(p.get("category", "")).strip() or "Uncategorised" for p in parts})

supplier_names = sorted({str(c.get("name", "")).strip() for c in customers if str(c.get("name", "")).strip()})

# ── Record New Purchase ───────────────────────────────────────────────────────
st.subheader("Record New Purchase")
purchase_mode = st.radio("Purchase mode", ["Existing Part", "New Part"], horizontal=True)

# Selections outside form so they update reactively
if purchase_mode == "Existing Part":
    selected_category = st.selectbox("Select Category", options=category_names, key="purch_cat_outer")
    category_rows = [p for p in parts if (str(p.get("category", "")).strip() or "Uncategorised") == selected_category]
    part_names = sorted({str(p.get("part_name", "")).strip() for p in category_rows if str(p.get("part_name", "")).strip()})

    if not part_names:
        st.info("No parts in this category.")
        st.stop()

    selected_part = st.selectbox("Select Part", options=part_names, key="purch_part_outer")
    matching_rows = [p for p in category_rows if str(p.get("part_name", "")).strip() == selected_part]
    existing_suppliers = sorted({str(r.get("supplier_name", "")).strip() for r in matching_rows if str(r.get("supplier_name", "")).strip()})
    default_category = selected_category
else:
    selected_part = None
    matching_rows = []
    existing_suppliers = []
    default_category = ""

with st.form("record_purchase_form", clear_on_submit=True):
    if purchase_mode == "New Part":
        part_name_input = st.text_input("Part Name")
        category_input = st.text_input("Category")
    else:
        part_name_input = selected_part
        category_input = default_category

    # Supplier: dropdown from customers + option to type new
    all_supplier_opts = ["-- Type new --"] + (existing_suppliers if purchase_mode == "Existing Part" else supplier_names)
    supplier_select = st.selectbox("Supplier (choose existing or type new)", options=all_supplier_opts)
    supplier_new = st.text_input("Or type new supplier name (overrides above if filled)")
    supplier_name = supplier_new.strip() if supplier_new.strip() else (supplier_select if supplier_select != "-- Type new --" else "")

    qty_purchased = st.number_input("Quantity Purchased", min_value=1, step=1, value=1)
    purchase_invoice = st.text_input("Purchase Invoice Number")
    purchase_date = st.date_input("Purchase Date", value=date.today())
    purchase_price = st.number_input("Purchase Price Per Unit", min_value=0.0, step=0.01, value=0.0, format="%.2f")
    sale_price = st.number_input("Sale Price Per Unit (for stock)", min_value=0.0, step=0.01, value=0.0, format="%.2f")
    purchase_bills = st.file_uploader("Upload Purchase Bill (optional)", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True, key="purch_bills")

    submit = st.form_submit_button("Record Purchase")
    if submit:
        final_part = str(part_name_input or "").strip()
        final_category = str(category_input or "").strip()

        if not final_part:
            st.error("Part Name is required.")
        elif not supplier_name:
            st.error("Supplier Name is required.")
        elif not purchase_invoice.strip():
            st.error("Invoice Number is required.")
        else:
            total_val = float(purchase_price) * int(qty_purchased)

            # Insert purchase record
            insert_record("purchase_records", {
                "date": purchase_date.isoformat(),
                "part_name": final_part,
                "category": final_category,
                "supplier_name": supplier_name,
                "quantity_purchased": str(int(qty_purchased)),
                "purchase_invoice_number": purchase_invoice.strip(),
                "purchase_price_per_unit": f"{float(purchase_price):.2f}",
                "total_purchase_value": f"{total_val:.2f}",
                "purchase_bill_images": files_to_json(purchase_bills),
            })

            # Update stock quantity
            existing = next((p for p in parts if str(p.get("part_name", "")).strip().lower() == final_part.lower() and str(p.get("supplier_name", "")).strip().lower() == supplier_name.lower()), None)
            if existing:
                new_qty = to_int(existing.get("quantity", "0")) + int(qty_purchased)
                update_record("parts", {"quantity": str(new_qty)}, "id", existing.get("id"))
            else:
                # New part — insert into parts table
                insert_record("parts", {
                    "part_name": final_part,
                    "category": final_category,
                    "supplier_name": supplier_name,
                    "quantity": str(int(qty_purchased)),
                    "unit_sale_price": f"{float(sale_price):.2f}",
                    "unit_purchase_price": f"{float(purchase_price):.2f}",
                    "date_added": purchase_date.isoformat(),
                })

            st.success(f"✅ Purchase recorded. Stock updated for {final_part}.")
            st.rerun()

st.markdown("---")

# ── View Purchase Records ─────────────────────────────────────────────────────
st.subheader("Purchase Records")
if not purchases:
    st.info("No purchase records yet.")
else:
    df = pd.DataFrame(purchases)
    df = df.drop(columns=["created_at"], errors="ignore")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    min_date = df["date"].min().date() if ("date" in df.columns and df["date"].notna().any()) else date.today()
    max_date = df["date"].max().date() if ("date" in df.columns and df["date"].notna().any()) else date.today()

    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("From", value=min_date, key="purch_start")
    with c2:
        end_date = st.date_input("To", value=max_date, key="purch_end")

    filtered = df.copy()
    if "date" in filtered.columns:
        filtered = filtered[(filtered["date"].dt.date >= start_date) & (filtered["date"].dt.date <= end_date)]

    total_val = pd.to_numeric(filtered.get("total_purchase_value", 0), errors="coerce").fillna(0).sum()
    st.metric("Total Purchase Value (filtered)", f"Rs {total_val:,.2f}")

    display_cols = [c for c in ["date", "part_name", "category", "supplier_name", "quantity_purchased", "purchase_invoice_number", "purchase_price_per_unit", "total_purchase_value"] if c in filtered.columns]
    out = filtered[display_cols].copy()
    if "date" in out.columns:
        out["date"] = out["date"].dt.date.astype(str)

    with st.expander(f"View {len(filtered)} records", expanded=False):
        st.dataframe(out, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Edit / Delete Purchase ────────────────────────────────────────────────────
st.subheader("Edit / Delete Purchase")
if not is_admin():
    st.info("🔐 Admin access required.")
elif not purchases:
    st.info("No records to edit.")
else:
    valid_purchases = [r for r in purchases if str(r.get("purchase_invoice_number") or "").strip()]
    if not valid_purchases:
        st.info("No records with invoice numbers found.")
    else:
        option_map = {}
        for rec in valid_purchases:
            inv = str(rec.get("purchase_invoice_number", "") or "").strip()
            dt = str(rec.get("date", "") or "").strip()
            pn = str(rec.get("part_name", "") or "").strip()
            label = f"{inv} | {dt} | {pn}"
            option_map[label] = rec

        selected_key = st.selectbox("Select purchase to edit/delete", options=list(option_map.keys()), key="edit_purch_select")
        selected = option_map[selected_key]

        with st.form("edit_purchase_form"):
            e_date = st.date_input("Date", value=pd.to_datetime(selected.get("date", str(date.today())), errors="coerce").date())
            e_part = st.text_input("Part Name", value=str(selected.get("part_name", "") or ""))
            e_category = st.text_input("Category", value=str(selected.get("category", "") or ""))
            e_supplier = st.text_input("Supplier Name", value=str(selected.get("supplier_name", "") or ""))
            e_qty = st.number_input("Quantity Purchased", min_value=1, step=1, value=max(1, to_int(selected.get("quantity_purchased", "1"))))
            e_invoice = st.text_input("Invoice Number", value=str(selected.get("purchase_invoice_number", "") or ""))
            e_price = st.number_input("Purchase Price Per Unit", min_value=0.0, step=0.01, value=to_float(selected.get("purchase_price_per_unit", "0")), format="%.2f")

            update_submit = st.form_submit_button("Update Purchase")
            if update_submit:
                update_record("purchase_records", {
                    "date": e_date.isoformat(),
                    "part_name": e_part.strip(),
                    "category": e_category.strip(),
                    "supplier_name": e_supplier.strip(),
                    "quantity_purchased": str(int(e_qty)),
                    "purchase_invoice_number": e_invoice.strip(),
                    "purchase_price_per_unit": f"{float(e_price):.2f}",
                    "total_purchase_value": f"{float(e_price) * int(e_qty):.2f}",
                }, "id", selected.get("id"))
                st.success("✅ Purchase updated.")
                st.rerun()

        confirm_delete = st.checkbox("Confirm delete this purchase record", key="purch_del_confirm")
        if st.button("Delete Purchase", type="secondary"):
            if not confirm_delete:
                st.error("Tick the confirm box first.")
            else:
                delete_record("purchase_records", "id", selected.get("id"))
                st.success("Deleted.")
                st.rerun()