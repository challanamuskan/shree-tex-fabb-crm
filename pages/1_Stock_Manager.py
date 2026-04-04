import base64
import json
from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import is_admin, require_login
from utils.constants import (
    CATEGORIES_HEADERS,
    CATEGORIES_TAB,
    PARTS_HEADERS,
    PARTS_TAB,
    PRICE_HISTORY_HEADERS,
    PRICE_HISTORY_TAB,
    PURCHASE_RECORDS_HEADERS,
    PURCHASE_RECORDS_TAB,
    RETURNS_HEADERS,
    RETURNS_TAB,
    SALES_RECORDS_HEADERS,
    SALES_RECORDS_TAB,
)
from utils.file_handler import base64_to_image, image_to_base64
from utils.sheets_db import (
    append_record,
    delete_record,
    get_or_create_worksheet,
    read_records,
    update_record,
)
from utils.ui import get_spreadsheet_connection, init_page

require_login()
init_page("Stock Manager")
st.title("Stock Manager")


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


def serialize_uploaded_files(files):
    encoded = []
    for file_obj in files or []:
        encoded.append(
            {
                "name": file_obj.name,
                "type": file_obj.type,
                "data": base64.b64encode(file_obj.getvalue()).decode(),
            }
        )
    return json.dumps(encoded, ensure_ascii=True)


spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

parts_ws = get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS)
categories_ws = get_or_create_worksheet(spreadsheet, CATEGORIES_TAB, CATEGORIES_HEADERS)
price_history_ws = get_or_create_worksheet(spreadsheet, PRICE_HISTORY_TAB, PRICE_HISTORY_HEADERS)
sales_ws = get_or_create_worksheet(spreadsheet, SALES_RECORDS_TAB, SALES_RECORDS_HEADERS)
purchase_ws = get_or_create_worksheet(spreadsheet, PURCHASE_RECORDS_TAB, PURCHASE_RECORDS_HEADERS)
returns_ws = get_or_create_worksheet(spreadsheet, RETURNS_TAB, RETURNS_HEADERS)

parts = read_records(parts_ws, PARTS_HEADERS)
categories = read_records(categories_ws, CATEGORIES_HEADERS)
price_history = read_records(price_history_ws, PRICE_HISTORY_HEADERS)
sales_records = read_records(sales_ws, SALES_RECORDS_HEADERS)
purchase_records = read_records(purchase_ws, PURCHASE_RECORDS_HEADERS)
returns_records = read_records(returns_ws, RETURNS_HEADERS)

st.subheader("Section A - Category Manager")
if categories:
    with st.expander(f"View Categories ({len(categories)})", expanded=False):
        st.dataframe(
            pd.DataFrame(categories).drop(columns=["_row"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No categories found. Add one to continue.")

with st.form("add_category_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        category_name = st.text_input("Category Name")
    with col2:
        category_description = st.text_input("Description (optional)")
    add_category = st.form_submit_button("Add New Category")
    if add_category:
        if not category_name.strip():
            st.error("Category Name is required.")
        else:
            existing = {
                r.get("Category_Name", "").strip().lower()
                for r in categories
            }
            if category_name.strip().lower() in existing:
                st.error("Category already exists.")
            else:
                append_record(
                    categories_ws,
                    CATEGORIES_HEADERS,
                    {
                        "Category_Name": category_name.strip(),
                        "Description": category_description.strip(),
                        "Created_Date": date.today().isoformat(),
                    },
                )
                st.success("Category added.")
                st.rerun()

if is_admin() and categories:
    delete_map = {
        f"{r.get('Category_Name', '').strip()}": r
        for r in categories
        if r.get("Category_Name", "").strip()
    }
    selected_delete = st.selectbox("Delete Category (admin only)", options=list(delete_map.keys()))
    if st.button("Delete category"):
        delete_record(categories_ws, delete_map[selected_delete]["_row"])
        st.success("Category deleted.")
        st.rerun()

st.markdown("---")
st.subheader("Section B - Add Part")

category_options = [r.get("Category_Name", "").strip() for r in categories if r.get("Category_Name", "").strip()]
if not category_options:
    st.warning("Add a category first.")
else:
    with st.form("add_part_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            form_category = st.selectbox("Category", options=category_options)
            part_name = st.text_input("Part Name")
            part_number = st.text_input("Part Number (optional)")
            supplier_name = st.text_input("Supplier Name")
            supplier_phone = st.text_input("Supplier Contact Phone")
            supplier_email = st.text_input("Supplier Contact Email")
            quantity = st.number_input("Quantity", min_value=0, step=1, value=0)
        with c2:
            reorder_level = st.number_input("Reorder Level", min_value=0, step=1, value=0)
            unit_purchase_price = st.number_input("Unit Purchase Price", min_value=0.0, step=0.01, format="%.2f")
            unit_sale_price = st.number_input("Unit Sale Price", min_value=0.0, step=0.01, format="%.2f")
            purchase_date = st.date_input("Purchase Date", value=date.today())
            image_file = st.file_uploader("Part Image (optional)", type=["jpg", "jpeg", "png"], key="part_img_file")
            camera_image = st.camera_input("Or capture image", key="part_img_camera")
            part_docs = st.file_uploader(
                "Part Documents (optional)",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True,
                key="part_docs",
            )

        add_part = st.form_submit_button("Add Part")
        if add_part:
            if not part_name.strip() or not supplier_name.strip():
                st.error("Part Name and Supplier Name are required.")
            else:
                image_source = image_file if image_file is not None else camera_image
                image_b64 = image_to_base64(image_source) if image_source is not None else ""
                docs_json = serialize_uploaded_files(part_docs)

                existing_row = next(
                    (
                        r
                        for r in parts
                        if r.get("Part_Name", "").strip().lower() == part_name.strip().lower()
                        and r.get("Supplier_Name", "").strip().lower() == supplier_name.strip().lower()
                    ),
                    None,
                )

                payload = {
                    "Part_Name": part_name.strip(),
                    "Part_Number": part_number.strip(),
                    "Category": form_category,
                    "Supplier_Name": supplier_name.strip(),
                    "Supplier_Phone": supplier_phone.strip(),
                    "Supplier_Email": supplier_email.strip(),
                    "Quantity": str(int(quantity)),
                    "Reorder_Level": str(int(reorder_level)),
                    "Unit_Purchase_Price": f"{float(unit_purchase_price):.2f}",
                    "Unit_Sale_Price": f"{float(unit_sale_price):.2f}",
                    "Purchase_Date": purchase_date.isoformat(),
                    "Product_Image": image_b64,
                    "Part_Documents": docs_json,
                }

                if existing_row:
                    payload["Quantity"] = str(to_int(existing_row.get("Quantity", "0")) + int(quantity))
                    update_record(parts_ws, existing_row["_row"], PARTS_HEADERS, payload)
                    st.success("Existing Part + Supplier updated with added quantity.")
                else:
                    append_record(parts_ws, PARTS_HEADERS, payload)
                    st.success("Part added.")
                st.rerun()

st.markdown("---")
st.subheader("Section C - Stock View")

parts_by_category = {}
for row in parts:
    category = row.get("Category", "Uncategorized").strip() or "Uncategorized"
    part = row.get("Part_Name", "Unnamed Part").strip() or "Unnamed Part"
    parts_by_category.setdefault(category, {}).setdefault(part, []).append(row)

low_stock_messages = []
for category_name, grouped_parts in parts_by_category.items():
    for part_name_key, supplier_rows in grouped_parts.items():
        total_stock = sum(to_int(r.get("Quantity", "0")) for r in supplier_rows)
        reorder_level_val = max(to_int(r.get("Reorder_Level", "0")) for r in supplier_rows)
        if total_stock <= reorder_level_val:
            low_stock_messages.append(
                f"⚠️ LOW STOCK ALERT: {part_name_key} — Only {total_stock} units remaining (Reorder level: {reorder_level_val})"
            )

if low_stock_messages:
    for msg in low_stock_messages:
        st.error(msg)
else:
    st.success("No low stock alerts.")

if not parts_by_category:
    st.info("No parts found.")
else:
    for category_name, grouped_parts in sorted(parts_by_category.items()):
        st.markdown(f"### {category_name}")
        part_rows = []
        for part_name_key, supplier_rows in sorted(grouped_parts.items()):
            total_stock = sum(to_int(r.get("Quantity", "0")) for r in supplier_rows)
            reorder_level_val = max(to_int(r.get("Reorder_Level", "0")) for r in supplier_rows)
            low_alert = "YES" if total_stock <= reorder_level_val else "NO"
            part_rows.append(
                {
                    "Part Name": part_name_key,
                    "Total Stock": total_stock,
                    "Reorder Level": reorder_level_val,
                    "Low Stock Alert": low_alert,
                }
            )

            with st.expander(f"{part_name_key} - Total: {total_stock}", expanded=False):
                first_image = next((r.get("Product_Image", "") for r in supplier_rows if r.get("Product_Image", "")), "")
                if first_image:
                    img = base64_to_image(first_image)
                    if img is not None:
                        st.image(img, width=140)

                breakdown = pd.DataFrame(
                    [
                        {
                            "Supplier": r.get("Supplier_Name", ""),
                            "Their Price": to_float(r.get("Unit_Purchase_Price", "0")),
                            "Their Quantity": to_int(r.get("Quantity", "0")),
                            "Contact": f"{r.get('Supplier_Phone', '').strip()} / {r.get('Supplier_Email', '').strip()}",
                        }
                        for r in supplier_rows
                    ]
                )
                st.dataframe(breakdown, use_container_width=True, hide_index=True)

        st.dataframe(pd.DataFrame(part_rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("Section D - Price Management (admin only)")
if not is_admin():
    st.info("Admin access required.")
elif not parts:
    st.info("No parts available for price management.")
else:
    part_names = sorted({r.get("Part_Name", "").strip() for r in parts if r.get("Part_Name", "").strip()})
    selected_part = st.selectbox("Part Name", options=part_names)
    supplier_names = sorted(
        {
            r.get("Supplier_Name", "").strip()
            for r in parts
            if r.get("Part_Name", "").strip() == selected_part and r.get("Supplier_Name", "").strip()
        }
    )
    selected_supplier = st.selectbox("Supplier", options=supplier_names)

    filtered_history = [
        h
        for h in price_history
        if h.get("Part_Name", "").strip() == selected_part
        and h.get("Supplier_Name", "").strip() == selected_supplier
    ]

    if filtered_history:
        st.markdown("Price History")
        st.dataframe(
            pd.DataFrame(filtered_history).drop(columns=["_row"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No price history for this part + supplier yet.")

    keep_history = st.checkbox("Keep price history", value=True)
    new_price = st.number_input("New purchase price", min_value=0.0, step=0.01, format="%.2f")
    if st.button("Update Price"):
        part_rows = [
            r
            for r in parts
            if r.get("Part_Name", "").strip() == selected_part
            and r.get("Supplier_Name", "").strip() == selected_supplier
        ]
        if not part_rows:
            st.error("Part + Supplier not found.")
        else:
            old_price = to_float(part_rows[0].get("Unit_Purchase_Price", "0"))
            for row in part_rows:
                payload = {
                    "Part_Name": row.get("Part_Name", "").strip(),
                    "Part_Number": row.get("Part_Number", "").strip(),
                    "Category": row.get("Category", "").strip(),
                    "Supplier_Name": row.get("Supplier_Name", "").strip(),
                    "Supplier_Phone": row.get("Supplier_Phone", "").strip(),
                    "Supplier_Email": row.get("Supplier_Email", "").strip(),
                    "Quantity": str(to_int(row.get("Quantity", "0"))),
                    "Reorder_Level": str(to_int(row.get("Reorder_Level", "0"))),
                    "Unit_Purchase_Price": f"{float(new_price):.2f}",
                    "Unit_Sale_Price": f"{to_float(row.get('Unit_Sale_Price', '0')):.2f}",
                    "Purchase_Date": row.get("Purchase_Date", "").strip(),
                    "Product_Image": row.get("Product_Image", ""),
                    "Part_Documents": row.get("Part_Documents", ""),
                }
                update_record(parts_ws, row["_row"], PARTS_HEADERS, payload)

            append_record(
                price_history_ws,
                PRICE_HISTORY_HEADERS,
                {
                    "Date": date.today().isoformat(),
                    "Part_Name": selected_part,
                    "Supplier_Name": selected_supplier,
                    "Old_Price": f"{old_price:.2f}",
                    "New_Price": f"{float(new_price):.2f}",
                    "Updated_By": st.session_state.get("username", "unknown"),
                },
            )
            if not keep_history:
                st.warning("History retention is enforced. All price updates are still stored.")
            st.success("Price updated and history saved.")
            st.rerun()

st.markdown("---")
st.subheader("Section E - Daily Activity")
activity_date = st.date_input("Select Date", value=date.today())
activity_key = activity_date.isoformat()

purchases_on_date = [r for r in purchase_records if str(r.get("Date", "")).strip() == activity_key]
sales_on_date = [r for r in sales_records if str(r.get("Date", "")).strip() == activity_key]
returns_on_date = [r for r in returns_records if str(r.get("Date", "")).strip() == activity_key]

st.markdown("Parts added/received on selected date")
if purchases_on_date:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Part Name": r.get("Part_Name", ""),
                    "Category": r.get("Category", ""),
                    "Quantity": r.get("Quantity_Purchased", ""),
                    "Party Name": r.get("Supplier_Name", ""),
                    "Value": r.get("Total_Purchase_Value", ""),
                }
                for r in purchases_on_date
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No purchases on selected date.")

st.markdown("Sales made on selected date")
if sales_on_date:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Part Name": r.get("Part_Name", ""),
                    "Category": r.get("Category", ""),
                    "Quantity": r.get("Quantity_Sold", ""),
                    "Party Name": r.get("Party_Name", ""),
                    "Value": r.get("Total_Sale_Value", ""),
                }
                for r in sales_on_date
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No sales on selected date.")

st.markdown("Returns on selected date")
if returns_on_date:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Part Name": r.get("Part_Name", ""),
                    "Category": r.get("Category", ""),
                    "Quantity": r.get("Quantity", ""),
                    "Party Name": r.get("Party_Supplier_Name", ""),
                    "Value": "",
                }
                for r in returns_on_date
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No returns on selected date.")
