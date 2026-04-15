from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.auth import require_login, is_admin
require_login()

from utils.supabase_db import fetch_table, insert_record, update_record, delete_record
from utils.ui import init_page

LEAD_STATUS_OPTIONS = ["New", "Contacted", "Interested", "Negotiation", "Won", "Lost"]


def parse_date(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return date.today()


init_page("Customers & Leads")
st.title("Customers & Leads")

raw_records = fetch_table("customers_leads")
records = [
    {
        "_row": r.get("id"),
        "Name": str(r.get("name", "") or ""),
        "Business Name": str(r.get("business_name", "") or ""),
        "Phone": str(r.get("phone", "") or ""),
        "Email": str(r.get("email", "") or ""),
        "Machine Type": str(r.get("machine_type", "") or ""),
        "Lead Status": str(r.get("lead_status", "") or ""),
        "Follow-up Date": str(r.get("follow_up_date", "") or ""),
        "Notes": str(r.get("notes", "") or ""),
    }
    for r in raw_records
]

st.subheader("Contacts")
if records:
    df = pd.DataFrame(records).drop(columns=["_row"])
    with st.expander(f"📋 View All Contacts ({len(records)} records) — click to expand", expanded=False):
        st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No contacts found.")

st.markdown("---")
st.subheader("Add Contact / Lead")
with st.form("add_contact_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Name")
        business_name = st.text_input("Business Name")
        phone = st.text_input("Phone")
        email = st.text_input("Email")
    with c2:
        machine_type = st.text_input("Machine Type")
        lead_status = st.selectbox("Lead Status", LEAD_STATUS_OPTIONS)
        follow_up = st.date_input("Follow-up Date", value=date.today())
        notes = st.text_area("Notes")

    add_submit = st.form_submit_button("Add Contact")
    if add_submit:
        if not name.strip():
            st.error("Name is required.")
        else:
            payload = {
                "name": name.strip(),
                "business_name": business_name.strip(),
                "phone": phone.strip(),
                "email": email.strip(),
                "machine_type": machine_type.strip(),
                "lead_status": lead_status,
                "follow_up_date": follow_up.isoformat(),
                "notes": notes.strip(),
            }
            try:
                insert_record("customers_leads", payload)
                st.success("Contact added successfully.")
                st.rerun()
            except Exception as exc:
                st.error(f"Error adding contact: {exc}")

st.markdown("---")
st.subheader("Edit / Delete Contact")
if records:
    if is_admin():
        option_map = {f"{r['Name']} | {r['Business Name']}": r for r in records}
        selected_key = st.selectbox("Select contact", list(option_map.keys()))
        selected = option_map[selected_key]

        with st.form("edit_contact_form"):
            c1, c2 = st.columns(2)
            with c1:
                e_name = st.text_input("Name", value=selected["Name"])
                e_business_name = st.text_input("Business Name", value=selected["Business Name"])
                e_phone = st.text_input("Phone", value=selected["Phone"])
                e_email = st.text_input("Email", value=selected["Email"])
            with c2:
                e_machine_type = st.text_input("Machine Type", value=selected["Machine Type"])
                current_status = selected["Lead Status"] if selected["Lead Status"] in LEAD_STATUS_OPTIONS else LEAD_STATUS_OPTIONS[0]
                e_lead_status = st.selectbox(
                    "Lead Status",
                    LEAD_STATUS_OPTIONS,
                    index=LEAD_STATUS_OPTIONS.index(current_status),
                )
                e_follow_up = st.date_input("Follow-up Date", value=parse_date(selected["Follow-up Date"]))
                e_notes = st.text_area("Notes", value=selected["Notes"])

            update_submit = st.form_submit_button("Update Contact")
            if update_submit:
                if not e_name.strip():
                    st.error("Name is required.")
                else:
                    payload = {
                        "name": e_name.strip(),
                        "business_name": e_business_name.strip(),
                        "phone": e_phone.strip(),
                        "email": e_email.strip(),
                        "machine_type": e_machine_type.strip(),
                        "lead_status": e_lead_status,
                        "follow_up_date": e_follow_up.isoformat(),
                        "notes": e_notes.strip(),
                    }
                    try:
                        update_record("customers_leads", payload, "id", selected["_row"])
                        st.success("Contact updated successfully.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Error updating contact: {exc}")

        confirm_delete = st.checkbox("Confirm delete selected contact")
        if st.button("Delete Contact", type="secondary"):
            if not confirm_delete:
                st.error("Please confirm deletion first.")
            else:
                try:
                    delete_record("customers_leads", "id", selected["_row"])
                    st.success("Contact deleted successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error deleting contact: {exc}")
    else:
        st.warning("🔐 Admin login required to edit or delete records.")
else:
    st.info("Add a contact to enable edit/delete actions.")
