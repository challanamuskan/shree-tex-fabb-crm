import base64
import json
from datetime import date

import pandas as pd
import streamlit as st

if "username" not in st.session_state or not st.session_state.get("username"):
    st.warning("Please login first.")
    st.stop()

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
from utils.supabase_db import (
    insert_record,
    delete_record,
    fetch_table,
    update_record,
    upsert_supplier_contact,
)
from utils.ui import check_admin_access, init_page

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


def _drive_direct_url(url: str) -> str:
    """Convert Drive shareable link to direct-access image URL for st.image()."""
    if "/file/d/" in url:
        try:
            file_id = url.split("/file/d/")[1].split("/")[0].split("?")[0]
            return f"https://drive.google.com/uc?export=view&id={file_id}"
        except (IndexError, AttributeError):
            pass
    return url


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


def map_parts(rows):
    mapped = []
    for r in rows:
        mapped.append(
            {
                "_row": r.get("id"),
                "cid": str(r.get("cid", "") or ""),
                "Category": str(r.get("category", "") or ""),
                "Part_Name": str(r.get("part_name", "") or ""),
                "Unit_Sale_Price": str(r.get("unit_sale_price", "") or ""),
                "Quantity": str(r.get("quantity", "") or ""),
                "status": str(r.get("status", "") or ""),
                "Date_Added": str(r.get("date_added", "") or ""),
                "Legacy_ID": str(r.get("legacy_id", "") or ""),
                "Price_Type": str(r.get("price_type", "") or ""),
                "Box_Number": str(r.get("box_number", "") or ""),
                "Supplier_Name": str(r.get("supplier_name", "") or ""),
                "image": str(r.get("image", "") or ""),
                "image_url": str(r.get("image_url", "") or ""),
                "Part_Number": "",
                "Supplier_Phone": "",
                "Supplier_Email": "",
                "Reorder_Level": "",
                "Unit_Purchase_Price": "",
                "Purchase_Date": "",
                "Product_Image": "",
                "Part_Documents": "",
            }
        )
    return mapped


def map_categories(rows):
    return [
        {
            "_row": r.get("id"),
            "Category_Name": str(r.get("category_name", "") or ""),
            "Description": str(r.get("description", "") or ""),
            "Created_Date": str(r.get("created_date", "") or ""),
        }
        for r in rows
    ]


def map_price_history(rows):
    return [
        {
            "_row": r.get("id"),
            "Date": str(r.get("date", "") or ""),
            "Part_Name": str(r.get("part_name", "") or ""),
            "Supplier_Name": str(r.get("supplier_name", "") or ""),
            "Old_Price": str(r.get("old_price", "") or ""),
            "New_Price": str(r.get("new_price", "") or ""),
            "Updated_By": str(r.get("updated_by", "") or ""),
        }
        for r in rows
    ]


def map_sales(rows):
    return [
        {
            "_row": r.get("id"),
            "Date": str(r.get("date", "") or ""),
            "Part_Name": str(r.get("part_name", "") or ""),
            "Category": str(r.get("category", "") or ""),
            "Supplier": str(r.get("supplier", "") or ""),
            "Quantity_Sold": str(r.get("quantity_sold", "") or ""),
            "Sale_Invoice_Number": str(r.get("sale_invoice_number", "") or ""),
            "Party_Name": str(r.get("party_name", "") or ""),
            "Sale_Price_Per_Unit": str(r.get("sale_price_per_unit", "") or ""),
            "Total_Sale_Value": str(r.get("total_sale_value", "") or ""),
            "Sale_Bill_Images": str(r.get("sale_bill_images", "") or ""),
        }
        for r in rows
    ]


def map_purchases(rows):
    return [
        {
            "_row": r.get("id"),
            "Date": str(r.get("date", "") or ""),
            "Part_Name": str(r.get("part_name", "") or ""),
            "Category": str(r.get("category", "") or ""),
            "Supplier_Name": str(r.get("supplier_name", "") or ""),
            "Quantity_Purchased": str(r.get("quantity_purchased", "") or ""),
            "Purchase_Invoice_Number": str(r.get("purchase_invoice_number", "") or ""),
            "Purchase_Price_Per_Unit": str(r.get("purchase_price_per_unit", "") or ""),
            "Total_Purchase_Value": str(r.get("total_purchase_value", "") or ""),
            "Purchase_Bill_Images": str(r.get("purchase_bill_images", "") or ""),
        }
        for r in rows
    ]


def map_returns(rows):
    return [
        {
            "_row": r.get("id"),
            "Date": str(r.get("date", "") or ""),
            "Part_Name": str(r.get("part_name", "") or ""),
            "Category": str(r.get("category", "") or ""),
            "Quantity": str(r.get("quantity", "") or ""),
            "Party_Supplier_Name": str(r.get("party_supplier_name", "") or ""),
        }
        for r in rows
    ]


_raw_parts = fetch_table("parts")
parts = map_parts(_raw_parts)
# Migration check: image_url column must exist in Supabase parts table.
# If missing, run in Supabase SQL editor:
#   ALTER TABLE parts ADD COLUMN IF NOT EXISTS image_url TEXT;
if _raw_parts and "image_url" not in _raw_parts[0] and is_admin():
    st.warning(
        "**Drive images disabled** — `image_url` column missing in Supabase. "
        "Run in Supabase SQL editor: "
        "`ALTER TABLE parts ADD COLUMN IF NOT EXISTS image_url TEXT;`"
    )
categories = map_categories(fetch_table("categories"))
price_history = map_price_history(fetch_table("price_history"))
sales_records = map_sales(fetch_table("sales_records"))
purchase_records = map_purchases(fetch_table("purchase_records"))
returns_records = map_returns(fetch_table("returns"))

# Auto-sync: extract unique categories from Parts and ensure they exist in Categories sheet
try:
    parts_data = parts
    parts_df = pd.DataFrame(parts_data)
    if "Category" in parts_df.columns:
        unique_cats_from_parts = set(
            parts_df["Category"]
            .replace(["", "nan", "None", "NaN"], pd.NA)
            .dropna()
            .str.strip()
            .unique()
        )

        # Get existing categories from Categories sheet
        cats_data = categories
        cats_df = pd.DataFrame(cats_data)
        existing_cats = (
            set(cats_df["Category_Name"].str.strip().tolist())
            if "Category_Name" in cats_df.columns and not cats_df.empty
            else set()
        )

        # Find categories in Parts but not in Categories sheet
        missing_cats = unique_cats_from_parts - existing_cats

        if missing_cats:
            for cat in sorted(missing_cats):
                insert_record(
                    "categories",
                    {
                        "category_name": cat,
                        "description": "",
                        "created_date": str(date.today()),
                    },
                )
            st.cache_data.clear()
except Exception:
    pass  # Silent fail — don't crash the page if sync fails

# ── Process any pending part-image upload (queued from Current Stock loop) ──
_pending = st.session_state.get("_pending_img_upload")
if "_pending_img_upload" in st.session_state:
    del st.session_state["_pending_img_upload"]
if _pending:
    update_record("parts", {"image_url": ""}, "id", _pending["row_id"])

st.subheader("Current Stock")
try:
    parts_tab_records = parts
except Exception:
    parts_tab_records = []

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
col3.metric("Total Stock Units", pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int).sum())

for cat in categories_list:
    cat_clean = str(cat).strip()
    if cat_clean in ["", "nan", "None", "NaN"] or cat_clean.startswith("—") or cat_clean.startswith("-"):
        continue  # skip junk categories

    cat_parts = df[df["Category"] == cat].copy()
    for col in ["Part_Name", "Quantity", "Unit_Sale_Price", "Supplier_Name"]:
        if col not in cat_parts.columns:
            cat_parts[col] = ""
    with st.expander(f"{cat_clean} ({len(cat_parts)} parts)", expanded=False):
        for _, row in cat_parts.iterrows():
            row_id = row.get("_row", "")
            img_col, info_col, upload_col = st.columns([1, 4, 2])
            with img_col:
                image_url = str(row.get("image_url", "") or "").strip()
                if image_url:
                    st.image(image_url, width=64)
            with info_col:
                st.markdown(
                    f"**{row.get('Part_Name', '')}** &nbsp;|&nbsp; "
                    f"Qty: {row.get('Quantity', '')} &nbsp;|&nbsp; "
                    f"₹{row.get('Unit_Sale_Price', '')} &nbsp;|&nbsp; "
                    f"*{row.get('Supplier_Name', '')}*"
                )
            with upload_col:
                st.caption("📷 upload image")
                _img_ver = st.session_state.get("_img_upload_ver", 0)
                uploaded_img = st.file_uploader(
                    "Upload image",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"stock_img_{row_id}_v{_img_ver}",
                    label_visibility="collapsed",
                )
                if uploaded_img is not None:
                    # Queue upload — processed at page-top on next run, widget key
                    # is versioned so it resets to empty after the rerun.
                    st.session_state["_pending_img_upload"] = {
                        "row_id": row_id,
                        "part_name": str(row.get("Part_Name", "")),
                        "category": str(row.get("Category", "")),
                        "data": uploaded_img.getvalue(),
                    }
                    st.session_state["_img_upload_ver"] = _img_ver + 1
                    st.rerun()

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
                insert_record(
                    "categories",
                    {
                        "category_name": category_name.strip(),
                        "description": category_description.strip(),
                        "created_date": date.today().isoformat(),
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
                    update_record(
                        "parts",
                        {
                            "cid": payload.get("cid", ""),
                            "category": payload.get("Category", ""),
                            "part_name": payload.get("Part_Name", ""),
                            "unit_sale_price": payload.get("Unit_Sale_Price", ""),
                            "quantity": payload.get("Quantity", ""),
                            "status": payload.get("status", ""),
                            "date_added": payload.get("Date_Added", ""),
                            "legacy_id": payload.get("Legacy_ID", ""),
                            "price_type": payload.get("Price_Type", ""),
                            "box_number": payload.get("Box_Number", ""),
                            "supplier_name": payload.get("Supplier_Name", ""),
                            "image": payload.get("image", ""),
                        },
                        "id",
                        existing_row["_row"],
                    )
                    upsert_supplier_contact(supplier_name, supplier_phone, supplier_email)
                    st.success("Existing Part + Supplier updated with added quantity.")
                else:
                    insert_record(
                        "parts",
                        {
                            "cid": payload.get("cid", ""),
                            "category": payload.get("Category", ""),
                            "part_name": payload.get("Part_Name", ""),
                            "unit_sale_price": payload.get("Unit_Sale_Price", ""),
                            "quantity": payload.get("Quantity", ""),
                            "status": payload.get("status", ""),
                            "date_added": payload.get("Date_Added", ""),
                            "legacy_id": payload.get("Legacy_ID", ""),
                            "price_type": payload.get("Price_Type", ""),
                            "box_number": payload.get("Box_Number", ""),
                            "supplier_name": payload.get("Supplier_Name", ""),
                            "image": payload.get("image", ""),
                        },
                    )
                    upsert_supplier_contact(supplier_name, supplier_phone, supplier_email)
                    # Upload image to Google Drive catalogue (silent if credentials missing)
                    if image_b64:
                        try:
                            from utils.drive_catalogue import (
                                CATALOGUE_FOLDER_ID,
                                upload_part_image_to_drive,
                            )
                            drive_url = upload_part_image_to_drive(
                                part_name.strip(), form_category, image_b64,
                                folder_id=CATALOGUE_FOLDER_ID,
                            )
                            if drive_url:
                                # Best-effort update — fetch newly inserted row by part_name + supplier
                                _new_rows = [
                                    r for r in fetch_table("parts")
                                    if str(r.get("part_name", "")).strip().lower() == part_name.strip().lower()
                                    and str(r.get("supplier_name", "")).strip().lower() == supplier_name.strip().lower()
                                ]
                                if _new_rows:
                                    update_record("parts", {"image_url": drive_url}, "id", _new_rows[-1]["id"])
                        except Exception:
                            pass
                    # Auto-insert purchase record so Daily Activity reflects this addition
                    if int(quantity) > 0:
                        insert_record("purchase_records", {
                            "date": purchase_date.isoformat(),
                            "part_name": part_name.strip(),
                            "category": form_category,
                            "supplier_name": supplier_name.strip(),
                            "quantity_purchased": str(int(quantity)),
                            "purchase_invoice_number": "STOCK-ADD",
                            "purchase_price_per_unit": f"{float(unit_purchase_price):.2f}",
                            "total_purchase_value": f"{float(unit_purchase_price) * int(quantity):.2f}",
                        })
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
                update_record(
                    "parts",
                    {
                        "cid": payload.get("cid", ""),
                        "category": payload.get("Category", ""),
                        "part_name": payload.get("Part_Name", ""),
                        "unit_sale_price": payload.get("Unit_Sale_Price", ""),
                        "quantity": payload.get("Quantity", ""),
                        "status": payload.get("status", ""),
                        "date_added": payload.get("Date_Added", ""),
                        "legacy_id": payload.get("Legacy_ID", ""),
                        "price_type": payload.get("Price_Type", ""),
                        "box_number": payload.get("Box_Number", ""),
                        "supplier_name": payload.get("Supplier_Name", ""),
                        "image": payload.get("image", ""),
                    },
                    "id",
                    row["_row"],
                )
            insert_record(
                "price_history",
                {
                    "date": date.today().isoformat(),
                    "part_name": selected_part,
                    "supplier_name": selected_supplier,
                    "old_price": f"{old_price:.2f}",
                    "new_price": f"{float(new_price):.2f}",
                    "updated_by": st.session_state.get("username", "unknown"),
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

purchases_on_date = [r for r in purchase_records if str(r.get("date", "") or r.get("Date", "")).strip() == activity_key]
sales_on_date = [r for r in sales_records if str(r.get("date", "") or r.get("Date", "")).strip() == activity_key]
returns_on_date = [r for r in returns_records if str(r.get("date", "") or r.get("Date", "")).strip() == activity_key]

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
    if st.button("📧 Send Low Stock Alert Email Now"):
        from utils.email_alerts import send_low_stock_email_alert

        with st.spinner("Sending..."):
            success, msg = send_low_stock_email_alert()
        if success:
            st.success(f"✅ {msg}")
        else:
            st.error(f"❌ {msg}")

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
                        update_record(
                            "parts",
                            {
                                "cid": payload.get("cid", ""),
                                "category": payload.get("Category", ""),
                                "part_name": payload.get("Part_Name", ""),
                                "unit_sale_price": payload.get("Unit_Sale_Price", ""),
                                "quantity": payload.get("Quantity", ""),
                                "status": payload.get("status", ""),
                                "date_added": payload.get("Date_Added", ""),
                                "legacy_id": payload.get("Legacy_ID", ""),
                                "price_type": payload.get("Price_Type", ""),
                                "box_number": payload.get("Box_Number", ""),
                                "supplier_name": payload.get("Supplier_Name", ""),
                                "image": payload.get("image", ""),
                            },
                            "id",
                            row_id,
                        )
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
            value=(selected_category_row.get("Description") or "").strip(),
            key="admin_category_description",
        )

        cat_col1, cat_col2 = st.columns(2)
        with cat_col1:
            if st.button("Update Category", key="admin_update_category"):
                update_record(
                    "categories",
                    {
                        "category_name": selected_category_name,
                        "description": edited_description.strip(),
                        "created_date": selected_category_row.get("Created_Date", "").strip() or date.today().isoformat(),
                    },
                    "id",
                    selected_category_row["_row"],
                )
                st.success("Category updated.")
                st.rerun()

        with cat_col2:
            if st.button("Delete Category", key="admin_delete_category"):
                delete_record(
                    "categories",
                    "id",
                    selected_category_row["_row"],
                )
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

            # Price edit form — file_uploader intentionally excluded to keep
            # submit button responsive (file_uploader inside st.form breaks it).
            # Keys are dynamic per part _row so switching parts resets widget state.
            _part_key = base_row.get("_row", "x")
            with st.form(f"edit_part_form_{_part_key}"):
                edit_purchase_price = st.number_input(
                    "Unit Purchase Price",
                    min_value=0.0,
                    step=0.01,
                    value=to_float(base_row.get("Unit_Purchase_Price", "0")),
                    format="%.2f",
                    key=f"admin_part_purchase_price_{_part_key}",
                )
                edit_sale_price = st.number_input(
                    "Unit Sale Price",
                    min_value=0.0,
                    step=0.01,
                    value=to_float(base_row.get("Unit_Sale_Price", "0")),
                    format="%.2f",
                    key=f"admin_part_sale_price_{_part_key}",
                )
                if st.form_submit_button("Save Part Changes"):
                    for row in selected_part_rows:
                        update_record(
                            "parts",
                            {
                                "cid": row.get("cid", "").strip(),
                                "category": row.get("Category", "").strip(),
                                "part_name": row.get("Part_Name", "").strip(),
                                "unit_purchase_price": f"{float(edit_purchase_price):.2f}",
                                "unit_sale_price": f"{float(edit_sale_price):.2f}",
                                "quantity": str(to_int(row.get("Quantity", "0"))),
                                "status": row.get("status", "").strip(),
                                "date_added": row.get("Date_Added", "").strip(),
                                "legacy_id": row.get("Legacy_ID", "").strip(),
                                "price_type": row.get("Price_Type", "").strip(),
                                "box_number": row.get("Box_Number", "").strip(),
                                "supplier_name": row.get("Supplier_Name", "").strip(),
                                "image_url": row.get("image_url", ""),
                            },
                            "id",
                            row["_row"],
                        )
                    st.success("Part prices updated.")
                    st.rerun()

            st.markdown("**📸 Upload Part Image**")
            _admin_img_ver = st.session_state.get("_admin_img_ver", 0)
            edit_image_file = st.file_uploader(
                "Upload Part Image (optional)",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"admin_part_image_upload_v{_admin_img_ver}",
            )
            if edit_image_file is not None:
                st.image(edit_image_file, width=200, caption="Preview")
                if st.button("💾 Save Image", key="save_image_btn"):
                    try:
                        import base64, io
                        from PIL import Image as PILImage
                        edit_image_file.seek(0)
                        img = PILImage.open(edit_image_file)
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        img.thumbnail((200, 200))
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=40)
                        image_b64 = base64.b64encode(buf.getvalue()).decode()
                        for row in selected_part_rows:
                            update_record("parts", {"image": image_b64}, "id", row["_row"])
                        st.success("✅ Image saved!")
                    except Exception as e:
                        st.error(f"Failed: {e}")

            if st.button("Delete Part", key="admin_delete_part"):
                for row in sorted(selected_part_rows, key=lambda x: x["_row"], reverse=True):
                    delete_record(
                        "parts",
                        "id",
                        row["_row"],
                    )
                st.success("Part deleted from stock records.")
                st.rerun()
else:
    st.info("🔐 Admin access required to edit or delete records.")
