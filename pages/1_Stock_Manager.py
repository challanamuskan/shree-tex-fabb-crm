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
    fetch_tab,
    fetch_sheet_data_by_name,
    get_or_create_worksheet,
    update_record,
)
from utils.ui import check_admin_access, get_spreadsheet_connection, init_page

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


def extract_image_payload(raw_value):
    text = str(raw_value or "").strip()
    if not text:
        return ""
    if text.startswith("data:image") and "," in text:
        return text.split(",", 1)[1]
    return text


spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

parts_ws = get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS)
categories_ws = get_or_create_worksheet(spreadsheet, CATEGORIES_TAB, CATEGORIES_HEADERS)
price_history_ws = get_or_create_worksheet(spreadsheet, PRICE_HISTORY_TAB, PRICE_HISTORY_HEADERS)
sales_ws = get_or_create_worksheet(spreadsheet, SALES_RECORDS_TAB, SALES_RECORDS_HEADERS)
purchase_ws = get_or_create_worksheet(spreadsheet, PURCHASE_RECORDS_TAB, PURCHASE_RECORDS_HEADERS)
returns_ws = get_or_create_worksheet(spreadsheet, RETURNS_TAB, RETURNS_HEADERS)

parts = fetch_sheet_data_by_name(PARTS_TAB, PARTS_HEADERS)
categories = fetch_sheet_data_by_name(CATEGORIES_TAB, CATEGORIES_HEADERS)
price_history = fetch_sheet_data_by_name(PRICE_HISTORY_TAB, PRICE_HISTORY_HEADERS)
sales_records = fetch_sheet_data_by_name(SALES_RECORDS_TAB, SALES_RECORDS_HEADERS)
purchase_records = fetch_sheet_data_by_name(PURCHASE_RECORDS_TAB, PURCHASE_RECORDS_HEADERS)
returns_records = fetch_sheet_data_by_name(RETURNS_TAB, RETURNS_HEADERS)

st.subheader("Current Stock")
try:
    parts_tab_records = fetch_tab("Parts")
except Exception:
    parts_tab_records = fetch_tab(PARTS_TAB)

df = pd.DataFrame(parts_tab_records)
if df.empty:
    df = pd.DataFrame(columns=PARTS_HEADERS)

if "Category" not in df.columns:
    df["Category"] = ""
if "Quantity" not in df.columns:
    df["Quantity"] = ""

df["Category"] = df["Category"].astype(str).replace(["", "nan", "None", "NaN"], "⚠️ Uncategorised")

categories_list = sorted(df["Category"].unique().tolist()) if not df.empty else []
col1, col2, col3 = st.columns(3)
col1.metric("Total Categories", len(categories_list))
col2.metric("Total Parts", len(df))
col3.metric("Total Stock Units", df["Quantity"].apply(lambda x: int(x) if str(x).isdigit() else 0).sum())

for cat in categories_list:
    cat_parts = df[df["Category"] == cat].copy()
    for col in ["Part_Name", "Quantity", "Unit_Sale_Price", "Supplier_Name"]:
        if col not in cat_parts.columns:
            cat_parts[col] = ""
    with st.expander(f"{cat} ({len(cat_parts)} parts)", expanded=False):
        st.dataframe(
            cat_parts[["Part_Name", "Quantity", "Unit_Sale_Price", "Supplier_Name"]],
            use_container_width=True,
            hide_index=True,
        )

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
                    "cid": "",
                    "Category": form_category,
                    "Part_Name": part_name.strip(),
                    "Unit_Sale_Price": f"{float(unit_sale_price):.2f}",
                    "Quantity": str(int(quantity)),
                    "status": "",
                    "Date_Added": purchase_date.isoformat(),
                    "Legacy_ID": "",
                    "Price_Type": "",
                    "Box_Number": "",
                    "Supplier_Name": supplier_name.strip(),
                    "image": image_b64,
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
st.caption("Use the Current Stock section above for grouped stock browsing, search, and category filtering.")

st.markdown("---")
st.subheader("Section D - Price Management (admin only)")
if not is_admin():
    st.info("Admin access required.")
elif not parts:
    st.info("No parts available for price management.")
else:
    categories_list = sorted({r.get("Category", "").strip() or "Uncategorised" for r in parts})
    selected_category = st.selectbox("Category", options=categories_list, key="price_cat")
    category_parts = [r for r in parts if (r.get("Category", "").strip() or "Uncategorised") == selected_category]
    part_names = sorted({r.get("Part_Name", "").strip() for r in category_parts if r.get("Part_Name", "").strip()})
    selected_part = st.selectbox("Part Name", options=part_names, key="price_part")
    supplier_names = sorted(
        {
            r.get("Supplier_Name", "").strip()
            for r in category_parts
            if r.get("Part_Name", "").strip() == selected_part and r.get("Supplier_Name", "").strip()
        }
    )
    selected_supplier = st.selectbox("Supplier", options=supplier_names, key="price_supplier")

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

st.markdown("---")
st.subheader("🛠️ Admin Controls (Edit / Delete)")

if check_admin_access():
    st.markdown("### 🔧 Fix Uncategorised Parts")
    uncategorised_rows = [
        r
        for r in parts
        if str(r.get("Category", "")).strip() in {"", "nan", "None", "NaN"}
    ]
    assignable_categories = [r.get("Category_Name", "").strip() for r in categories if r.get("Category_Name", "").strip()]

    if st.button("🔧 Fix Uncategorised Parts", key="fix_uncategorised_btn"):
        st.session_state["show_uncategorised_fix"] = True

    if st.session_state.get("show_uncategorised_fix", False):
        if not uncategorised_rows:
            st.success("No uncategorised parts found.")
        elif not assignable_categories:
            st.warning("No categories available. Add categories first.")
        else:
            with st.form("fix_uncategorised_form"):
                assignments = {}
                for row in uncategorised_rows:
                    row_id = row.get("_row")
                    label = f"{row.get('Part_Name', 'Unnamed')} | Supplier: {row.get('Supplier_Name', '')} | Qty: {row.get('Quantity', '')}"
                    assignments[row_id] = st.selectbox(
                        label,
                        options=assignable_categories,
                        key=f"assign_category_{row_id}",
                    )

                if st.form_submit_button("Save Category Assignments"):
                    updated = 0
                    for row in uncategorised_rows:
                        row_id = row.get("_row")
                        payload = {header: str(row.get(header, "") or "") for header in PARTS_HEADERS}
                        payload["Category"] = assignments.get(row_id, payload.get("Category", ""))
                        update_record(parts_ws, row_id, PARTS_HEADERS, payload)
                        updated += 1
                    st.success(f"Updated category for {updated} parts.")
                    st.session_state["show_uncategorised_fix"] = False
                    st.rerun()

    st.markdown("### Edit / Delete Category")
    category_map = {
        r.get("Category_Name", "").strip(): r
        for r in categories
        if r.get("Category_Name", "").strip()
    }

    if not category_map:
        st.info("No categories available.")
    else:
        selected_category_name = st.selectbox(
            "Select Category",
            options=sorted(category_map.keys()),
            key="admin_category_select",
        )
        selected_category_row = category_map[selected_category_name]
        edited_description = st.text_input(
            "Category Description",
            value=selected_category_row.get("Description", "").strip(),
            key="admin_category_description",
        )

        cat_col1, cat_col2 = st.columns(2)
        with cat_col1:
            if st.button("Update Category", key="admin_update_category"):
                update_record(
                    categories_ws,
                    selected_category_row["_row"],
                    CATEGORIES_HEADERS,
                    {
                        "Category_Name": selected_category_name,
                        "Description": edited_description.strip(),
                        "Created_Date": selected_category_row.get("Created_Date", "").strip() or date.today().isoformat(),
                    },
                )
                st.success("Category updated.")
                st.rerun()

        with cat_col2:
            if st.button("Delete Category", key="admin_delete_category"):
                delete_record(categories_ws, selected_category_row["_row"])
                st.success("Category deleted from Categories sheet.")
                st.rerun()

    st.markdown("### Edit / Delete Part")
    category_options = sorted({(r.get("Category", "").strip() or "Uncategorised") for r in parts})
    if not category_options:
        st.info("No parts available.")
    else:
        edit_category = st.selectbox("Part Category", options=category_options, key="admin_part_category")
        part_candidates = [r for r in parts if (r.get("Category", "").strip() or "Uncategorised") == edit_category]
        part_names = sorted({r.get("Part_Name", "").strip() for r in part_candidates if r.get("Part_Name", "").strip()})

        if not part_names:
            st.info("No parts found in selected category.")
        else:
            edit_part_name = st.selectbox("Part Name", options=part_names, key="admin_part_name")
            selected_part_rows = [r for r in part_candidates if r.get("Part_Name", "").strip() == edit_part_name]
            base_row = selected_part_rows[0]

            edit_purchase_price = st.number_input(
                "Unit Purchase Price",
                min_value=0.0,
                step=0.01,
                value=to_float(base_row.get("Unit_Purchase_Price", "0")),
                format="%.2f",
                key="admin_part_purchase_price",
            )
            edit_sale_price = st.number_input(
                "Unit Sale Price",
                min_value=0.0,
                step=0.01,
                value=to_float(base_row.get("Unit_Sale_Price", "0")),
                format="%.2f",
                key="admin_part_sale_price",
            )
            edit_image_file = st.file_uploader(
                "Upload Part Image (optional)",
                type=["jpg", "jpeg", "png", "webp"],
                key="admin_part_image_upload",
            )

            updated_image_b64 = ""
            if edit_image_file is not None:
                updated_image_b64 = base64.b64encode(edit_image_file.getvalue()).decode()

            part_col1, part_col2 = st.columns(2)
            with part_col1:
                if st.button("Save Part Changes", key="admin_update_part"):
                    for row in selected_part_rows:
                        update_record(
                            parts_ws,
                            row["_row"],
                            PARTS_HEADERS,
                            {
                                "Part_Name": row.get("Part_Name", "").strip(),
                                "cid": row.get("cid", "").strip(),
                                "Category": row.get("Category", "").strip(),
                                "Unit_Sale_Price": f"{float(edit_sale_price):.2f}",
                                "Quantity": str(to_int(row.get("Quantity", "0"))),
                                "status": row.get("status", "").strip(),
                                "Date_Added": row.get("Date_Added", "").strip(),
                                "Legacy_ID": row.get("Legacy_ID", "").strip(),
                                "Price_Type": row.get("Price_Type", "").strip(),
                                "Box_Number": row.get("Box_Number", "").strip(),
                                "Supplier_Name": row.get("Supplier_Name", "").strip(),
                                "image": updated_image_b64 if updated_image_b64 else row.get("image", ""),
                            },
                        )
                    st.success("Part details updated for all supplier rows.")
                    st.rerun()

            with part_col2:
                if st.button("Delete Part", key="admin_delete_part"):
                    for row in sorted(selected_part_rows, key=lambda x: x["_row"], reverse=True):
                        delete_record(parts_ws, row["_row"])
                    st.success("Part deleted from stock records.")
                    st.rerun()
else:
    st.info("🔐 Admin access required to edit or delete records.")
