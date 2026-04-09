import base64
import json
from datetime import date

import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.supabase_db import delete_record, fetch_table, insert_record, update_record
from utils.ui import init_page

require_login()
init_page("Returns")
st.title("Returns")


def to_int(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


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
returns_data = fetch_table("returns")

category_names = sorted({str(c.get("category_name", "")).strip() for c in categories if str(c.get("category_name", "")).strip()})
if not category_names:
    category_names = sorted({str(p.get("category", "")).strip() or "uncategorised" for p in parts})

if not category_names:
    st.info("No parts found.")
    st.stop()

sale_tab, purchase_tab = st.tabs(["Sale Returns", "Purchase Returns"])

with sale_tab:
    with st.form("sale_return_form", clear_on_submit=True):
        invoice_no = st.text_input("Original Sale Invoice Number")
        sale_category = st.selectbox("Category", options=category_names, key="sale_return_category")
        category_rows = [p for p in parts if (str(p.get("category", "")).strip() or "uncategorised") == sale_category]
        sale_parts = sorted({str(p.get("part_name", "")).strip() for p in category_rows if str(p.get("part_name", "")).strip()})

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
                rows = [r for r in category_rows if str(r.get("part_name", "")).strip() == part_name]
                if not rows:
                    st.error("Part not found.")
                else:
                    target = sorted(rows, key=lambda r: to_int(r.get("quantity", "0")), reverse=True)[0]
                    new_qty = to_int(target.get("quantity", "0")) + int(qty)
                    update_record("parts", {"quantity": str(new_qty)}, "id", target.get("id"))

                    insert_record(
                        "returns",
                        {
                            "date": return_date.isoformat(),
                            "type": "Sale Return",
                            "part_name": str(target.get("part_name", "")).strip(),
                            "category": sale_category,
                            "supplier_name": str(target.get("supplier_name", "")).strip(),
                            "quantity": str(int(qty)),
                            "invoice_number": invoice_no.strip(),
                            "party_supplier_name": party_name.strip(),
                            "reason": reason.strip(),
                            "return_document": files_to_json(docs),
                        },
                    )
                    st.success("Sale return recorded and stock increased.")
                    st.rerun()

with purchase_tab:
    with st.form("purchase_return_form", clear_on_submit=True):
        invoice_no = st.text_input("Original Purchase Invoice Number")
        purchase_category = st.selectbox("Category", options=category_names, key="purchase_return_category")
        category_rows = [r for r in parts if (str(r.get("category", "")).strip() or "uncategorised") == purchase_category]
        part_names = sorted({str(r.get("part_name", "")).strip() for r in category_rows if str(r.get("part_name", "")).strip()})

        if not part_names:
            st.info("No parts found in the selected category.")
            st.form_submit_button("Record Purchase Return", disabled=True)
        else:
            part_name = st.selectbox("Part Name", options=part_names, key="purchase_return_part")
            suppliers_for_part = sorted(
                {
                    str(r.get("supplier_name", "")).strip()
                    for r in category_rows
                    if str(r.get("part_name", "")).strip() == part_name and str(r.get("supplier_name", "")).strip()
                }
            )
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
                        if str(r.get("part_name", "")).strip() == part_name and str(r.get("supplier_name", "")).strip() == supplier_name
                    ),
                    None,
                )
                if not target:
                    st.error("Matching Part + Supplier row not found.")
                else:
                    current_qty = to_int(target.get("quantity", "0"))
                    if int(qty) > current_qty:
                        st.error(f"Quantity returned exceeds stock ({current_qty}).")
                    else:
                        update_record("parts", {"quantity": str(current_qty - int(qty))}, "id", target.get("id"))

                        insert_record(
                            "returns",
                            {
                                "date": return_date.isoformat(),
                                "type": "Purchase Return",
                                "part_name": str(target.get("part_name", "")).strip(),
                                "category": purchase_category,
                                "supplier_name": str(target.get("supplier_name", "")).strip(),
                                "quantity": str(int(qty)),
                                "invoice_number": invoice_no.strip(),
                                "party_supplier_name": supplier_name,
                                "reason": reason.strip(),
                                "return_document": files_to_json(docs),
                            },
                        )
                        st.success("Purchase return recorded and stock decreased.")
                        st.rerun()

st.markdown("---")
st.subheader("Returns View")
if not returns_data:
    st.info("No return records found.")
else:
    returns_df = pd.DataFrame(returns_data)
    display_cols = [
        "date",
        "type",
        "part_name",
        "category",
        "supplier_name",
        "quantity",
        "invoice_number",
        "party_supplier_name",
        "reason",
    ]
    existing_cols = [c for c in display_cols if c in returns_df.columns]
    st.dataframe(returns_df[existing_cols], use_container_width=True, hide_index=True)

st.markdown("---")
st.subheader("Edit / Delete Return")
if not returns_data:
    st.info("No return records available.")
else:
    option_map = {}
    for rec in returns_data:
        label = f"{rec.get('invoice_number', '')} | {rec.get('date', '')} | {rec.get('type', '')}"
        option_map[label] = rec

    selected_key = st.selectbox("Select return record", options=list(option_map.keys()))
    selected = option_map[selected_key]

    with st.form("edit_return_form"):
        e_date = st.date_input("Date", value=pd.to_datetime(selected.get("date", date.today()), errors="coerce").date())
        e_type = st.selectbox("Type", options=["Sale Return", "Purchase Return"], index=0 if str(selected.get("type", "Sale Return")) == "Sale Return" else 1)
        e_part = st.text_input("Part Name", value=str(selected.get("part_name", "")))
        e_category = st.text_input("Category", value=str(selected.get("category", "")))
        e_supplier = st.text_input("Supplier Name", value=str(selected.get("supplier_name", "")))
        e_qty = st.number_input("Quantity", min_value=1, step=1, value=max(1, to_int(selected.get("quantity", "1"))))
        e_invoice = st.text_input("Invoice Number", value=str(selected.get("invoice_number", "")))
        e_party = st.text_input("Party/Supplier Name", value=str(selected.get("party_supplier_name", "")))
        e_reason = st.text_input("Reason", value=str(selected.get("reason", "")))

        update_submit = st.form_submit_button("Update Return")
        if update_submit:
            payload = {
                "date": e_date.isoformat(),
                "type": e_type,
                "part_name": e_part.strip(),
                "category": e_category.strip(),
                "supplier_name": e_supplier.strip(),
                "quantity": str(int(e_qty)),
                "invoice_number": e_invoice.strip(),
                "party_supplier_name": e_party.strip(),
                "reason": e_reason.strip(),
            }
            update_record("returns", payload, "id", selected.get("id"))
            st.success("Return record updated.")
            st.rerun()

    confirm_delete = st.checkbox("Confirm delete selected return", key="returns_delete_confirm")
    if st.button("Delete Return", type="secondary"):
        if not confirm_delete:
            st.error("Please confirm deletion first.")
        else:
            delete_record("returns", "id", selected.get("id"))
            st.success("Return record deleted.")
            st.rerun()
