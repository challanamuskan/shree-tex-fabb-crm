from datetime import date, datetime

import pandas as pd
import streamlit as st

from utils.auth import require_login, is_admin
require_login()

from utils.constants import CONTACTS_HEADERS, CONTACTS_TAB
from utils.sheets_db import (
    append_record,
    delete_record,
    get_cached_records_by_title,
    get_or_create_worksheet,
    update_record,
)
from utils.ui import (
    get_spreadsheet_connection,
    init_page,
)

LEAD_STATUS_OPTIONS = ["New", "Contacted", "Interested", "Negotiation", "Won", "Lost"]


def parse_date(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return date.today()


init_page("Customers & Leads")
st.title("Customers & Leads")

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

worksheet = get_or_create_worksheet(spreadsheet, CONTACTS_TAB, CONTACTS_HEADERS)
records = get_cached_records_by_title(worksheet.title, CONTACTS_HEADERS)

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
                "Name": name.strip(),
                "Business Name": business_name.strip(),
                "Phone": phone.strip(),
                "Email": email.strip(),
                "Machine Type": machine_type.strip(),
                "Lead Status": lead_status,
                "Follow-up Date": follow_up.isoformat(),
                "Notes": notes.strip(),
            }
            try:
                append_record(worksheet, CONTACTS_HEADERS, payload)
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
                        "Name": e_name.strip(),
                        "Business Name": e_business_name.strip(),
                        "Phone": e_phone.strip(),
                        "Email": e_email.strip(),
                        "Machine Type": e_machine_type.strip(),
                        "Lead Status": e_lead_status,
                        "Follow-up Date": e_follow_up.isoformat(),
                        "Notes": e_notes.strip(),
                    }
                    try:
                        update_record(worksheet, selected["_row"], CONTACTS_HEADERS, payload)
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
                    delete_record(worksheet, selected["_row"])
                    st.success("Contact deleted successfully.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error deleting contact: {exc}")
    else:
        st.warning("🔐 Admin login required to edit or delete records.")
else:
    st.info("Add a contact to enable edit/delete actions.")
