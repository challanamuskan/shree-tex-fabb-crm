from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.auth import is_admin, require_login
from utils.gmail_sender import get_gmail_service, send_email
from utils.supabase_db import fetch_table, insert_record, update_record, delete_record
from utils.ui import init_page
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


def build_po_email(po_number, supplier_name, delivery_date, items, total_amount):
    subject = f"Purchase Order — {po_number} | Satyam Tex Fabb"
    lines = [
        f"Dear {supplier_name},",
        "",
        f"Please process Purchase Order {po_number} with the following items:",
        "",
    ]
    for item in items:
        lines.append(f"- {item.get('part_name', '')}: Qty {item.get('quantity_ordered', '')}, Unit Rs {item.get('unit_price', '')}, Total Rs {item.get('line_total', '')}")
    lines += [
        "",
        f"Total Order Value: Rs {total_amount}",
        f"Expected Delivery: {delivery_date}",
        "",
        "Kindly confirm receipt and dispatch timeline.",
        "",
        "Regards,",
        "Satyam Tex Fabb, Bhilwara, Rajasthan",
    ]
    return subject, "\n".join(lines)


def build_po_whatsapp(supplier_name, po_number, delivery_date, items, total_amount):
    lines = [f"Dear {supplier_name}, PO {po_number} from Satyam Tex Fabb:"]
    for item in items:
        lines.append(f"- {item.get('part_name', '')}: {item.get('quantity_ordered', '')} qty @ Rs {item.get('unit_price', '')}")
    lines += [f"Total: Rs {total_amount}", f"Expected Delivery: {delivery_date}", "Please confirm."]
    return "\n".join(lines)


records = fetch_table("purchase_orders")
parts_records = fetch_table("parts")
categories_records = fetch_table("categories")
customers = fetch_table("customers")

category_names = sorted({str(r.get("category_name", "")).strip() for r in categories_records if str(r.get("category_name", "")).strip()})
if not category_names:
    category_names = sorted({str(r.get("category", "")).strip() or "Uncategorised" for r in parts_records})

# Build supplier list from customers table
supplier_options_from_db = sorted({str(c.get("name", "")).strip() for c in customers if str(c.get("name", "")).strip()})
supplier_contact_map = {
    str(c.get("name", "")).strip(): {
        "email": str(c.get("email", "") or "").strip(),
        "phone": str(c.get("phone", "") or "").strip(),
    }
    for c in customers if str(c.get("name", "")).strip()
}

st.subheader("Create Purchase Order")

# Supplier selection outside form for reactivity
st.markdown("**Step 1 — Select Supplier**")
sup_opts = ["-- Type new --"] + supplier_options_from_db
sup_select = st.selectbox("Supplier (from your contacts)", options=sup_opts, key="po_sup_select")
sup_new = st.text_input("Or type new supplier name", key="po_sup_new")
supplier_name = sup_new.strip() if sup_new.strip() else (sup_select if sup_select != "-- Type new --" else "")

# Show auto-filled contact details
supplier_email_prefill = ""
supplier_phone_prefill = ""
if supplier_name in supplier_contact_map:
    contact = supplier_contact_map[supplier_name]
    supplier_email_prefill = contact.get("email", "")
    supplier_phone_prefill = contact.get("phone", "")
    if supplier_email_prefill or supplier_phone_prefill:
        st.caption(f"📧 {supplier_email_prefill or 'no email'} | 📱 {supplier_phone_prefill or 'no phone'}")

# Category + Part outside form
st.markdown("**Step 2 — Select Part**")
selected_category = st.selectbox("Category", options=category_names, key="po_cat_outer")
category_rows = [p for p in parts_records if (str(p.get("category", "")).strip() or "Uncategorised") == selected_category]
part_names_in_cat = sorted({str(p.get("part_name", "")).strip() for p in category_rows if str(p.get("part_name", "")).strip()})

if part_names_in_cat:
    selected_part = st.selectbox("Part", options=part_names_in_cat, key="po_part_outer")
    matching = [p for p in category_rows if str(p.get("part_name", "")).strip() == selected_part]
    default_price = to_float(matching[0].get("unit_sale_price", "0")) if matching else 0.0
else:
    selected_part = ""
    default_price = 0.0

st.markdown("**Step 3 — Order Details**")
with st.form("create_po_form", clear_on_submit=True):
    po_number = st.text_input("PO Number", value=f"PO-{date.today().strftime('%Y%m%d')}")
    part_name_input = st.text_input("Part Name", value=selected_part or "")
    qty_ordered = st.number_input("Quantity Ordered", min_value=1, step=1, value=1)
    unit_price = st.number_input("Unit Price (Rs)", min_value=0.0, step=0.01, value=default_price, format="%.2f")
    order_date = st.date_input("Order Date", value=date.today())
    expected_delivery = st.date_input("Expected Delivery", value=date.today())
    status = st.selectbox("Status", STATUS_OPTIONS)
    supplier_email = st.text_input("Supplier Email", value=supplier_email_prefill)
    supplier_phone = st.text_input("Supplier Phone/WhatsApp", value=supplier_phone_prefill)

    send_method = st.radio("Send PO via", ["Save Only", "Email", "WhatsApp", "Both Email & WhatsApp"], horizontal=True)

    submit_po = st.form_submit_button("Create Purchase Order")
    if submit_po:
        if not supplier_name:
            st.error("Supplier name is required.")
        elif not part_name_input.strip():
            st.error("Part name is required.")
        else:
            line_total = float(unit_price) * int(qty_ordered)
            items = [{"part_name": part_name_input.strip(), "quantity_ordered": str(int(qty_ordered)), "unit_price": f"{float(unit_price):.2f}", "line_total": f"{line_total:.2f}"}]

            insert_record("purchase_orders", {
                "supplier": supplier_name,
                "invoice_number": po_number.strip(),
                "part_name": part_name_input.strip(),
                "quantity_ordered": str(int(qty_ordered)),
                "unit_price": f"{float(unit_price):.2f}",
                "line_total": f"{line_total:.2f}",
                "total_order_value": f"{line_total:.2f}",
                "order_date": order_date.isoformat(),
                "expected_delivery": expected_delivery.isoformat(),
                "status": status,
            })

            po_subject, po_body = build_po_email(po_number, supplier_name, expected_delivery.isoformat(), items, f"{line_total:.2f}")

            if send_method in ["Email", "Both Email & WhatsApp"] and supplier_email.strip():
                try:
                    gmail = get_gmail_service()
                    send_email(gmail, supplier_email.strip(), po_subject, po_body)
                    st.success(f"✅ PO emailed to {supplier_email.strip()}")
                except Exception as e:
                    st.error(f"Email failed: {e}")

            if send_method in ["WhatsApp", "Both Email & WhatsApp"] and supplier_phone.strip():
                wa_msg = build_po_whatsapp(supplier_name, po_number, expected_delivery.isoformat(), items, f"{line_total:.2f}")
                wa_link = generate_whatsapp_link(supplier_phone.strip(), wa_msg)
                st.link_button("📲 Open WhatsApp to send PO", wa_link)

            st.success("✅ Purchase Order created.")
            st.rerun()

st.markdown("---")

# ── View Purchase Orders ──────────────────────────────────────────────────────
st.subheader("All Purchase Orders")
if not records:
    st.info("No purchase orders yet.")
else:
    df = pd.DataFrame(records)
    df = df.drop(columns=["invoice_document", "created_at"], errors="ignore")

    status_filter = st.selectbox("Filter by Status", ["All"] + STATUS_OPTIONS, key="po_status_filter")
    if status_filter != "All" and "status" in df.columns:
        df = df[df["status"] == status_filter]

    display_cols = [c for c in ["supplier", "invoice_number", "part_name", "quantity_ordered", "unit_price", "total_order_value", "order_date", "expected_delivery", "status"] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

st.markdown("---")

# ── Edit / Delete PO ──────────────────────────────────────────────────────────
st.subheader("Edit / Delete Purchase Order")
if not is_admin():
    st.info("🔐 Admin access required.")
elif not records:
    st.info("No records to edit.")
else:
    option_map = {f"{r.get('invoice_number', '')} | {r.get('supplier', '')} | {r.get('part_name', '')}": r for r in records}
    selected_key = st.selectbox("Select PO", options=list(option_map.keys()), key="edit_po_select")
    selected = option_map[selected_key]

    with st.form("edit_po_form"):
        e_supplier = st.text_input("Supplier", value=str(selected.get("supplier", "") or ""))
        e_part = st.text_input("Part Name", value=str(selected.get("part_name", "") or ""))
        e_qty = st.number_input("Qty Ordered", min_value=1, step=1, value=max(1, to_int(selected.get("quantity_ordered", "1"))))
        e_price = st.number_input("Unit Price", min_value=0.0, step=0.01, value=to_float(selected.get("unit_price", "0")), format="%.2f")
        e_delivery = st.date_input("Expected Delivery", value=parse_date(selected.get("expected_delivery", "")))
        cur_status = str(selected.get("status", "Ordered") or "Ordered")
        if cur_status not in STATUS_OPTIONS:
            cur_status = "Ordered"
        e_status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(cur_status))

        update_submit = st.form_submit_button("Update PO")
        if update_submit:
            line_total = float(e_price) * int(e_qty)
            update_record("purchase_orders", {
                "supplier": e_supplier.strip(),
                "part_name": e_part.strip(),
                "quantity_ordered": str(int(e_qty)),
                "unit_price": f"{float(e_price):.2f}",
                "line_total": f"{line_total:.2f}",
                "total_order_value": f"{line_total:.2f}",
                "expected_delivery": e_delivery.isoformat(),
                "status": e_status,
            }, "id", selected.get("id"))
            st.success("✅ PO updated.")
            st.rerun()

    confirm_del = st.checkbox("Confirm delete this PO", key="po_del_confirm")
    if st.button("Delete PO", type="secondary"):
        if not confirm_del:
            st.error("Tick confirm first.")
        else:
            delete_record("purchase_orders", "id", selected.get("id"))
            st.success("Deleted.")
            st.rerun()