import base64
import json
from datetime import date

import streamlit as st

from utils.auth import require_login
from utils.constants import CATEGORIES_HEADERS, CATEGORIES_TAB, PARTS_HEADERS, PARTS_TAB, RETURNS_HEADERS, RETURNS_TAB
from utils.sheets_db import append_record, fetch_sheet_data_by_name, get_or_create_worksheet, update_record
from utils.ui import get_spreadsheet_connection, init_page

require_login()
init_page("Returns")
st.title("↩️ Returns")


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
category_names = sorted({p.get("Category_Name", "").strip() for p in categories if p.get("Category_Name", "").strip()})
if not category_names:
    category_names = sorted({p.get("Category", "").strip() or "Uncategorised" for p in parts})

if not category_names:
    st.info("No parts found.")
    st.stop()

sale_tab, purchase_tab = st.tabs(["Sale Returns", "Purchase Returns"])

with sale_tab:
    with st.form("sale_return_form", clear_on_submit=True):
        invoice_no = st.text_input("Original Sale Invoice Number")
        sale_category = st.selectbox("Category", options=category_names, key="sale_return_category")
        category_rows = [p for p in parts if (p.get("Category", "").strip() or "Uncategorised") == sale_category]
        sale_parts = sorted({p.get("Part_Name", "").strip() for p in category_rows if p.get("Part_Name", "").strip()})
        if not sale_parts:
            st.info("No parts found in the selected category.")
            st.form_submit_button("Record Sale Return", disabled=True)
        else:
            part_name = st.selectbox("Part Name", options=sale_parts, key="sale_return_part")
            qty = st.number_input("Quantity Returned", min_value=1, step=1, value=1)
            return_date = st.date_input("Return Date", value=date.today(), key="sale_return_date")
            party_name = st.text_input("Party Name")
            reason = st.text_input("Reason for Return")
            docs = st.file_uploader(
                "Upload Return Document (optional)",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True,
                key="sale_return_docs",
            )

            submit_sale_return = st.form_submit_button("Record Sale Return")
            if submit_sale_return:
                rows = [r for r in category_rows if r.get("Part_Name", "").strip() == part_name]
                if not rows:
                    st.error("Part not found.")
                else:
                    target = sorted(rows, key=lambda r: to_int(r.get("Quantity", "0")), reverse=True)[0]
                    new_qty = to_int(target.get("Quantity", "0")) + int(qty)
                    update_record(
                        get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS),
                        target["_row"],
                        PARTS_HEADERS,
                        {
                            "Part_Name": target.get("Part_Name", "").strip(),
                            "Part_Number": target.get("Part_Number", "").strip(),
                            "Category": target.get("Category", "").strip(),
                            "Supplier_Name": target.get("Supplier_Name", "").strip(),
                            "Supplier_Phone": target.get("Supplier_Phone", "").strip(),
                            "Supplier_Email": target.get("Supplier_Email", "").strip(),
                            "Quantity": str(new_qty),
                            "Reorder_Level": str(to_int(target.get("Reorder_Level", "0"))),
                            "Unit_Purchase_Price": f"{to_float(target.get('Unit_Purchase_Price', '0')):.2f}",
                            "Unit_Sale_Price": f"{to_float(target.get('Unit_Sale_Price', '0')):.2f}",
                            "Purchase_Date": target.get("Purchase_Date", "").strip(),
                            "Product_Image": target.get("Product_Image", ""),
                            "Part_Documents": target.get("Part_Documents", ""),
                        },
                    )

                    append_record(
                        get_or_create_worksheet(spreadsheet, RETURNS_TAB, RETURNS_HEADERS),
                        RETURNS_HEADERS,
                        {
                            "Date": return_date.isoformat(),
                            "Type": "Sale Return",
                            "Part_Name": target.get("Part_Name", "").strip(),
                            "Category": sale_category,
                            "Supplier_Name": target.get("Supplier_Name", "").strip(),
                            "Quantity": str(int(qty)),
                            "Invoice_Number": invoice_no.strip(),
                            "Party_Supplier_Name": party_name.strip(),
                            "Reason": reason.strip(),
                            "Return_Documents": files_to_json(docs),
                        },
                    )
                    st.success("Sale return recorded and stock increased.")
                    st.rerun()

with purchase_tab:
    with st.form("purchase_return_form", clear_on_submit=True):
        invoice_no = st.text_input("Original Purchase Invoice Number")
        purchase_category = st.selectbox("Category", options=category_names, key="purchase_return_category")
        category_rows = [r for r in parts if (r.get("Category", "").strip() or "Uncategorised") == purchase_category]
        part_names = sorted({r.get("Part_Name", "").strip() for r in category_rows if r.get("Part_Name", "").strip()})
        if not part_names:
            st.info("No parts found in the selected category.")
            st.form_submit_button("Record Purchase Return", disabled=True)
        else:
            part_name = st.selectbox("Part Name", options=part_names, key="purchase_return_part")
            suppliers_for_part = sorted({r.get("Supplier_Name", "").strip() for r in category_rows if r.get("Part_Name", "").strip() == part_name and r.get("Supplier_Name", "").strip()})
            supplier_name = st.selectbox("Supplier Name", options=suppliers_for_part if suppliers_for_part else [""], key="purchase_return_supplier")
            qty = st.number_input("Quantity Returned", min_value=1, step=1, value=1, key="purchase_return_qty")
            return_date = st.date_input("Return Date", value=date.today(), key="purchase_return_date")
            reason = st.text_input("Reason for Return")
            docs = st.file_uploader(
                "Upload Return Document (optional)",
                type=["jpg", "jpeg", "png", "pdf"],
                accept_multiple_files=True,
                key="purchase_return_docs",
            )

            submit_purchase_return = st.form_submit_button("Record Purchase Return")
            if submit_purchase_return:
                target = next(
                    (
                        r
                        for r in category_rows
                        if r.get("Part_Name", "").strip() == part_name and r.get("Supplier_Name", "").strip() == supplier_name
                    ),
                    None,
                )
                if not target:
                    st.error("Matching Part + Supplier row not found.")
                else:
                    current_qty = to_int(target.get("Quantity", "0"))
                    if int(qty) > current_qty:
                        st.error(f"Quantity returned exceeds stock ({current_qty}).")
                    else:
                        update_record(
                            get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS),
                            target["_row"],
                            PARTS_HEADERS,
                            {
                                "Part_Name": target.get("Part_Name", "").strip(),
                                "Part_Number": target.get("Part_Number", "").strip(),
                                "Category": target.get("Category", "").strip(),
                                "Supplier_Name": target.get("Supplier_Name", "").strip(),
                                "Supplier_Phone": target.get("Supplier_Phone", "").strip(),
                                "Supplier_Email": target.get("Supplier_Email", "").strip(),
                                "Quantity": str(current_qty - int(qty)),
                                "Reorder_Level": str(to_int(target.get("Reorder_Level", "0"))),
                                "Unit_Purchase_Price": f"{to_float(target.get('Unit_Purchase_Price', '0')):.2f}",
                                "Unit_Sale_Price": f"{to_float(target.get('Unit_Sale_Price', '0')):.2f}",
                                "Purchase_Date": target.get("Purchase_Date", "").strip(),
                                "Product_Image": target.get("Product_Image", ""),
                                "Part_Documents": target.get("Part_Documents", ""),
                            },
                        )

                        append_record(
                            get_or_create_worksheet(spreadsheet, RETURNS_TAB, RETURNS_HEADERS),
                            RETURNS_HEADERS,
                            {
                                "Date": return_date.isoformat(),
                                "Type": "Purchase Return",
                                "Part_Name": target.get("Part_Name", "").strip(),
                                "Category": purchase_category,
                                "Supplier_Name": target.get("Supplier_Name", "").strip(),
                                "Quantity": str(int(qty)),
                                "Invoice_Number": invoice_no.strip(),
                                "Party_Supplier_Name": supplier_name,
                                "Reason": reason.strip(),
                                "Return_Documents": files_to_json(docs),
                            },
                        )
                        st.success("Purchase return recorded and stock decreased.")
                        st.rerun()
