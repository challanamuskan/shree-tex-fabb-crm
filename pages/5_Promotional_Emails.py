from datetime import datetime

from google import genai
import pandas as pd
import streamlit as st

from utils.constants import (
    CONTACTS_HEADERS,
    CONTACTS_TAB,
    EMAIL_LOG_HEADERS,
    EMAIL_LOG_TAB,
)
from utils.gmail_sender import get_gmail_service, send_email
from utils.sheets_db import append_record, get_or_create_worksheet, read_records
from utils.ui import get_spreadsheet_connection, init_page
from utils.whatsapp_sender import send_whatsapp_message

EMAIL_TYPE = "Promotional"
OPEN_LEAD_STATUSES = {"new", "contacted", "interested", "negotiation"}


init_page("Promotional Emails")
st.title("Promotional Emails")

spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

contacts_ws = get_or_create_worksheet(spreadsheet, CONTACTS_TAB, CONTACTS_HEADERS)
email_log_ws = get_or_create_worksheet(spreadsheet, EMAIL_LOG_TAB, EMAIL_LOG_HEADERS)

contacts = read_records(contacts_ws, CONTACTS_HEADERS)

audience_rows = []
for contact in contacts:
    email = contact.get("Email", "").strip()
    phone = contact.get("Phone", "").strip()
    if not email and not phone:
        continue

    audience_rows.append(
        {
            "Select": False,
            "Name": contact.get("Name", "").strip(),
            "Business Name": contact.get("Business Name", "").strip(),
            "Email": email,
            "Phone": phone,
            "Machine Type": contact.get("Machine Type", "").strip(),
            "Lead Status": contact.get("Lead Status", "").strip(),
        }
    )

if not audience_rows:
    st.info("No contacts with email addresses found in Customers & Leads.")
    st.stop()

all_df = pd.DataFrame(audience_rows)

st.subheader("Audience Filter")
filter_mode = st.radio(
    "Filter by",
    options=["All Customers", "Active Leads", "Specific Machine Type"],
    horizontal=True,
)

filtered_df = all_df.copy()
if filter_mode == "Active Leads":
    filtered_df = filtered_df[
        filtered_df["Lead Status"].str.lower().isin(OPEN_LEAD_STATUSES)
    ]
elif filter_mode == "Specific Machine Type":
    machine_types = sorted([m for m in all_df["Machine Type"].unique().tolist() if m])
    selected_machine_type = st.selectbox("Machine Type", machine_types)
    filtered_df = filtered_df[filtered_df["Machine Type"] == selected_machine_type]

st.caption(f"Recipients available: {len(filtered_df)}")

edited_df = st.data_editor(
    filtered_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    disabled=["Name", "Business Name", "Email", "Phone", "Machine Type", "Lead Status"],
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", default=False),
    },
)

selected_df = edited_df[edited_df["Select"]]
st.caption(f"Selected recipients: {len(selected_df)}")

st.markdown("---")
st.subheader("Send Campaign")
send_mode = st.radio(
    "Choose sending method",
    options=["Email Only", "WhatsApp Only", "Both Email & WhatsApp"],
    horizontal=True,
)

st.subheader("Compose Message")
topic = st.text_input("Campaign Topic", value="New arrivals in textile machinery parts")
default_subject = st.session_state.get(
    "promo_subject",
    "Exclusive Update from Shree Tex Fabb",
)
default_body = st.session_state.get(
    "promo_body",
    (
        "Dear [Customer Name],\n\n"
        "Greetings from Shree Tex Fabb!\n\n"
        "[Custom message here]\n\n"
        "We value your continued association with us and look forward to serving your machinery parts requirements.\n\n"
        "For orders or enquiries, please contact us anytime.\n\n"
        "Warm regards,\n"
        "Shree Tex Fabb\n"
        "Bhilwara, Rajasthan"
    ),
)
subject = st.text_input("Subject", value=default_subject)
body = st.text_area(
    "Email Body",
    value=default_body,
    height=260,
)

gen_col1, gen_col2 = st.columns(2)
with gen_col1:
    if st.button("Generate Email Body"):
        if not topic.strip():
            st.error("Please enter a topic to generate email body.")
        else:
            try:
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"""Write a professional promotional email for a textile machinery parts business called Shree Tex Fabb based in Bhilwara, Rajasthan.

Topic: {topic}

Requirements:
- Professional and warm tone
- Mention Shree Tex Fabb by name
- Relevant to textile machinery parts industry
- Include a clear call to action
- End with professional signature for Shree Tex Fabb, Bhilwara
- Return ONLY the email body text, no subject line, no extra commentary
- Keep it concise, under 200 words"""
                )
                email_body = (response.text or "").strip()
                if not email_body:
                    st.error("Gemini did not return email body text.")
                else:
                    st.session_state["promo_body"] = email_body
                    st.rerun()
            except KeyError:
                st.error("GEMINI_API_KEY not found in Streamlit secrets.")
            except Exception as exc:
                st.error(f"Error generating email body: {exc}")

with gen_col2:
    if st.button("Generate Subject Line"):
        if not topic.strip():
            st.error("Please enter a topic to generate subject line.")
        else:
            try:
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                subject_response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"Write only a short professional email subject line (max 8 words) for a promotional email about: {topic} for a textile machinery parts business. Return ONLY the subject line, nothing else.",
                )
                email_subject = (subject_response.text or "").strip()
                if not email_subject:
                    st.error("Gemini did not return subject line text.")
                else:
                    st.session_state["promo_subject"] = email_subject
                    st.rerun()
            except KeyError:
                st.error("GEMINI_API_KEY not found in Streamlit secrets.")
            except Exception as exc:
                st.error(f"Error generating subject line: {exc}")

st.subheader("Preview")
preview_name = "Customer"
if not selected_df.empty:
    preview_name = selected_df.iloc[0]["Name"]
preview_body = body.replace("[Customer Name]", preview_name)
st.markdown(f"**Subject:** {subject}")
st.text_area("Preview Body", value=preview_body, height=220, disabled=True)


def personalize(text, row):
    result = text
    result = result.replace("[Customer Name]", str(row["Name"]))
    result = result.replace("[Business Name]", str(row["Business Name"]))
    result = result.replace("[Machine Type]", str(row["Machine Type"]))
    return result


if st.button("Send to All Selected", type="primary"):
    if selected_df.empty:
        st.error("Please select at least one recipient.")
        st.stop()

    if not subject.strip() or not body.strip():
        st.error("Subject and body are required.")
        st.stop()

    result_rows = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if send_mode in ["Email Only", "Both Email & WhatsApp"]:
        try:
            gmail_service = get_gmail_service()
        except Exception as exc:
            st.error(f"Gmail authentication failed: {exc}")
            st.stop()

    for _, row in selected_df.iterrows():
        recipient_name = str(row["Name"]).strip()
        recipient_email = str(row["Email"]).strip()
        recipient_phone = str(row["Phone"]).strip()
        personalized_body = personalize(body, row)

        email_status = "Not Sent"
        whatsapp_status = "Not Sent"

        if send_mode in ["Email Only", "Both Email & WhatsApp"]:
            if not recipient_email:
                email_status = "No Email"
            else:
                try:
                    send_email(gmail_service, recipient_email, subject, personalized_body)
                    st.success(f"Email sent to {recipient_name} ({recipient_email})")
                    append_record(
                        email_log_ws,
                        EMAIL_LOG_HEADERS,
                        {
                            "Timestamp": timestamp,
                            "Email Type": EMAIL_TYPE,
                            "Recipient Name": recipient_name,
                            "Recipient Email": recipient_email,
                            "Subject": subject,
                            "Status": "Sent",
                            "Error": "",
                        },
                    )
                    email_status = "Sent"
                except Exception as exc:
                    st.error(f"Email failed for {recipient_name}: {str(exc)}")
                    email_status = "Failed"

        if send_mode in ["WhatsApp Only", "Both Email & WhatsApp"]:
            if not recipient_phone:
                whatsapp_status = "No Phone"
            else:
                success, msg = send_whatsapp_message(recipient_phone, personalized_body, wait_time=30)
                if success:
                    st.success(f"WhatsApp sent to {recipient_name} ({recipient_phone})")
                    whatsapp_status = "Sent"
                else:
                    st.error(msg)
                    whatsapp_status = "Failed"

        result_rows.append(
            {
                "Recipient": recipient_name,
                "Email Status": email_status,
                "WhatsApp Status": whatsapp_status,
                "Email": recipient_email,
                "Phone": recipient_phone,
            }
        )

    st.markdown("### Send Results")
    results_df = pd.DataFrame(result_rows)
    with st.expander(f"📋 Campaign Results ({len(result_rows)} records) — click to expand", expanded=False):
        st.dataframe(results_df, use_container_width=True, hide_index=True)
