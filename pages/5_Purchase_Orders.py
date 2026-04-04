from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.auth import is_admin, require_login
from utils.constants import (
    CATEGORIES_HEADERS,
    CATEGORIES_TAB,
    CONTACTS_HEADERS,
    CONTACTS_TAB,
    PARTS_HEADERS,
    PARTS_TAB,
    PURCHASE_ORDERS_HEADERS,
    PURCHASE_ORDERS_TAB,
)
from utils.file_handler import upload_and_scan_widget
from utils.gmail_sender import get_gmail_service, send_email
from utils.sheets_db import append_record, delete_record, get_cached_records, get_or_create_worksheet, update_record
from utils.ui import get_spreadsheet_connection, init_page
from utils.whatsapp_sender import generate_whatsapp_link

require_login()
init_page("Purchase Orders")
st.title("Purchase Orders")

STATUS_OPTIONS = ["Ordered", "In Transit", "Delivered", "Cancelled"]


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


def parse_date(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return date.today()


def build_po_email(po_number, delivery_date, items, total_amount):
    subject = f"Purchase Order — {po_number} | Satyam Tex Fabb"
    lines = []
    lines.append("Dear Sir/Madam,")
    lines.append("")
    lines.append(f"Please process Purchase Order {po_number} with the following line items:")
    lines.append("")
    for item in items:
        lines.append(
            f"- {item.get('Part Name', '')}: Qty {item.get('Quantity Ordered', '')}, Unit ₹{item.get('Unit Price', '')}, Line ₹{item.get('Line Total', '')}"
        )
    lines.append("")
    lines.append(f"Total Order Value: ₹{total_amount}")
    lines.append(f"Expected Delivery Date: {delivery_date}")
    lines.append("")
    lines.append("Kindly confirm receipt and dispatch timeline.")
    lines.append("")
    lines.append("Regards,")
    lines.append("Satyam Tex Fabb")
    return subject, "\n".join(lines)


def build_po_whatsapp(name, po_number, delivery_date, items, total_amount):
    lines = [f"Dear {name}, Purchase Order {po_number} from Satyam Tex Fabb:"]
    for item in items:
        lines.append(f"- {item.get('Part Name', '')}: {item.get('Quantity Ordered', '')} qty")
    lines.append(f"Total: ₹{total_amount}")
    lines.append(f"Expected Delivery: {delivery_date}")
    lines.append("Please confirm receipt.")
    return "\n".join(lines)


spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

worksheet = get_or_create_worksheet(spreadsheet, PURCHASE_ORDERS_TAB, PURCHASE_ORDERS_HEADERS)
parts_ws = get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS)
categories_ws = get_or_create_worksheet(spreadsheet, CATEGORIES_TAB, CATEGORIES_HEADERS)
contacts_ws = get_or_create_worksheet(spreadsheet, CONTACTS_TAB, CONTACTS_HEADERS)

records = get_cached_records(worksheet, worksheet.title, PURCHASE_ORDERS_HEADERS)
parts_records = get_cached_records(parts_ws, parts_ws.title, PARTS_HEADERS)
categories_records = get_cached_records(categories_ws, categories_ws.title, CATEGORIES_HEADERS)
contact_records = get_cached_records(contacts_ws, contacts_ws.title, CONTACTS_HEADERS)
category_names = sorted({r.get("Category_Name", "").strip() for r in categories_records if r.get("Category_Name", "").strip()})
if not category_names:
    category_names = sorted({r.get("Category", "").strip() or "Uncategorised" for r in parts_records})

if not parts_records:
    st.info("No parts found. Add stock items first to create purchase orders.")
    st.stop()

st.subheader("Orders")
if records:
    df = pd.DataFrame(records).drop(columns=["_row", "Invoice_Document"], errors="ignore")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No purchase orders found.")

st.markdown("---")
st.subheader("Create Purchase Order")
if "po_product_count" not in st.session_state:
    st.session_state["po_product_count"] = 1

bill_b64, scan_data = upload_and_scan_widget("Supplier Invoice", "po_invoice")
header_c1, header_c2 = st.columns(2)
with header_c1:
    supplier = st.text_input("Supplier Name", value=scan_data.get("party_name", ""), key="po_supplier")
    invoice_number = st.text_input("PO Number", value=scan_data.get("invoice_number", ""), key="po_invoice_number")
with header_c2:
    order_date = st.date_input("Order Date", value=date.today(), key="po_order_date")
    expected_delivery = st.date_input("Expected Delivery", value=date.today(), key="po_expected_delivery")

status = st.selectbox("Status", STATUS_OPTIONS, key="po_status")

if st.button("Add Another Product"):
    st.session_state["po_product_count"] += 1

product_rows = []
for idx in range(st.session_state["po_product_count"]):
    st.markdown(f"Product {idx + 1}")
    p1, p2, p3 = st.columns([2, 2, 1])
    with p1:
        p_category = st.selectbox("Category", options=category_names, key=f"po_category_{idx}")
    category_rows = [r for r in parts_records if (r.get("Category", "").strip() or "Uncategorised") == p_category]
    category_part_names = sorted({r.get("Part_Name", "").strip() for r in category_rows if r.get("Part_Name", "").strip()})
    with p2:
        p_name = st.selectbox("Part Name", options=category_part_names if category_part_names else [""], key=f"po_part_name_{idx}")
    with p3:
        p_qty = st.number_input("Quantity", min_value=1, step=1, value=1, key=f"po_qty_{idx}")
    p_unit_price = st.number_input("Unit Price", min_value=0.0, step=0.01, format="%.2f", key=f"po_unit_price_{idx}")
    line_total = int(p_qty) * float(p_unit_price)
    st.caption(f"Line Total: ₹{line_total:,.2f}")
    product_rows.append(
        {
            "Category": p_category,
            "Part Name": p_name.strip(),
            "Quantity Ordered": int(p_qty),
            "Unit Price": f"{float(p_unit_price):.2f}",
            "Line Total": f"{line_total:.2f}",
        }
    )

valid_products = [p for p in product_rows if p["Part Name"]]
total_order_value = sum(to_float(p["Line Total"]) for p in valid_products)

if valid_products:
    st.dataframe(pd.DataFrame(valid_products), use_container_width=True, hide_index=True)
st.markdown(f"Total Order Value: ₹{total_order_value:,.2f}")

if st.button("Create Order"):
    if not supplier.strip() or not invoice_number.strip() or not valid_products:
        st.error("Supplier, PO Number and at least one product are required.")
    else:
        for item in valid_products:
            append_record(
                worksheet,
                PURCHASE_ORDERS_HEADERS,
                {
                    "Supplier": supplier.strip(),
                    "Invoice Number": invoice_number.strip(),
                    "Part Name": item["Part Name"],
                    "Quantity Ordered": str(item["Quantity Ordered"]),
                    "Unit Price": item["Unit Price"],
                    "Line Total": item["Line Total"],
                    "Total Order Value": f"{total_order_value:.2f}",
                    "Order Date": order_date.isoformat(),
                    "Expected Delivery": expected_delivery.isoformat(),
                    "Status": status,
                    "Invoice_Document": bill_b64,
                },
            )
        st.session_state["last_po"] = {
            "po_number": invoice_number.strip(),
            "supplier": supplier.strip(),
            "delivery": expected_delivery.isoformat(),
            "items": valid_products,
            "total": f"{total_order_value:.2f}",
        }
        st.success("Purchase order created.")
        st.session_state["po_product_count"] = 1
        st.rerun()

st.markdown("---")

last_po = st.session_state.get("last_po")
if last_po:
    st.subheader("Send Purchase Order")
    send_to = st.radio("Recipient Type", ["Send to Supplier", "Send to Customer", "Send to Custom Contact"], horizontal=True)

    recipient_name = ""
    recipient_email = ""
    recipient_phone = ""

    if send_to == "Send to Supplier":
        supplier_contacts = {}
        for row in parts_records:
            name = row.get("Supplier_Name", "").strip()
            if name and name not in supplier_contacts:
                supplier_contacts[name] = {
                    "email": row.get("Supplier_Email", "").strip(),
                    "phone": row.get("Supplier_Phone", "").strip(),
                }
        if supplier_contacts:
            pick = st.selectbox("Supplier", options=list(supplier_contacts.keys()))
            recipient_name = pick
            recipient_email = supplier_contacts[pick].get("email", "")
            recipient_phone = supplier_contacts[pick].get("phone", "")
        else:
            st.info("No suppliers found from Parts sheet.")

    elif send_to == "Send to Customer":
        customer_map = {}
        for row in contact_records:
            name = row.get("Name", "").strip()
            if name:
                customer_map[name] = {
                    "email": row.get("Email", "").strip(),
                    "phone": row.get("Phone", "").strip(),
                }
        if customer_map:
            pick = st.selectbox("Customer", options=list(customer_map.keys()))
            recipient_name = pick
            recipient_email = customer_map[pick].get("email", "")
            recipient_phone = customer_map[pick].get("phone", "")
        else:
            st.info("No customers found.")

    else:
        recipient_name = st.text_input("Name", value="Contact")
        recipient_email = st.text_input("Email")
        recipient_phone = st.text_input("Phone")

    po_subject, po_body = build_po_email(
        last_po["po_number"],
        last_po["delivery"],
        last_po["items"],
        last_po["total"],
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📧 Send via Email"):
            if not recipient_email.strip():
                st.error("Recipient email is missing.")
            else:
                try:
                    service = get_gmail_service()
                    send_email(service, recipient_email.strip(), po_subject, po_body)
                    st.success(f"Purchase order email sent to {recipient_email.strip()}.")
                except Exception as exc:
                    st.error(f"Email failed: {exc}")

    with c2:
        whatsapp_msg = build_po_whatsapp(
            recipient_name or "Contact",
            last_po["po_number"],
            last_po["delivery"],
            last_po["items"],
            last_po["total"],
        )
        if recipient_phone.strip():
            st.link_button("💬 Send via WhatsApp", generate_whatsapp_link(recipient_phone.strip(), whatsapp_msg))
        else:
            st.caption("Enter/select a phone number to enable WhatsApp link.")

st.markdown("---")
st.subheader("Edit / Delete Purchase Order")
if records and is_admin():
    option_map = {
        f"{r.get('Supplier', '').strip()} | {r.get('Invoice Number', '').strip()} | {r.get('Part Name', '').strip()}": r
        for r in records
    }
    selected_key = st.selectbox("Select order", options=list(option_map.keys()))
    selected = option_map[selected_key]

    with st.form("edit_po_form"):
        c1, c2 = st.columns(2)
        with c1:
            e_supplier = st.text_input("Supplier", value=selected.get("Supplier", ""))
            e_invoice_number = st.text_input("Invoice Number", value=selected.get("Invoice Number", ""))
            e_part_name = st.text_input("Part Name", value=selected.get("Part Name", ""))
            e_quantity = st.number_input("Quantity Ordered", min_value=1, step=1, value=max(1, to_int(selected.get("Quantity Ordered", "1"))))
        with c2:
            e_unit_price = st.number_input("Unit Price", min_value=0.0, step=0.01, format="%.2f", value=to_float(selected.get("Unit Price", "0")))
            e_order_date = st.date_input("Order Date", value=parse_date(selected.get("Order Date", "")))
            e_expected_delivery = st.date_input("Expected Delivery", value=parse_date(selected.get("Expected Delivery", "")))
            current_status = selected.get("Status", STATUS_OPTIONS[0])
            status_idx = STATUS_OPTIONS.index(current_status) if current_status in STATUS_OPTIONS else 0
            e_status = st.selectbox("Status", STATUS_OPTIONS, index=status_idx)

        update_submit = st.form_submit_button("Update Order")
        if update_submit:
            line_total = int(e_quantity) * float(e_unit_price)
            payload = {
                "Supplier": e_supplier.strip(),
                "Invoice Number": e_invoice_number.strip(),
                "Part Name": e_part_name.strip(),
                "Quantity Ordered": str(int(e_quantity)),
                "Unit Price": f"{float(e_unit_price):.2f}",
                "Line Total": f"{line_total:.2f}",
                "Total Order Value": selected.get("Total Order Value", f"{line_total:.2f}"),
                "Order Date": e_order_date.isoformat(),
                "Expected Delivery": e_expected_delivery.isoformat(),
                "Status": e_status,
                "Invoice_Document": selected.get("Invoice_Document", ""),
            }
            update_record(worksheet, selected["_row"], PURCHASE_ORDERS_HEADERS, payload)
            st.success("Order updated.")
            st.rerun()

    confirm_delete = st.checkbox("Confirm delete selected order")
    if st.button("Delete Order"):
        if not confirm_delete:
            st.error("Please confirm deletion first.")
        else:
            delete_record(worksheet, selected["_row"])
            st.success("Order deleted.")
            st.rerun()
elif records:
    st.info("Admin access required for edit/delete.")
else:
    st.info("Create an order first.")
