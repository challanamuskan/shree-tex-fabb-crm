from datetime import datetime

import pandas as pd
import streamlit as st

from utils.auth import require_login, is_admin
require_login()

from utils.gmail_sender import get_gmail_service, send_email
<<<<<<< Updated upstream
from utils.supabase_db import append_record, fetch_sheet_data_by_name, fetch_table, get_or_create_worksheet
from utils.ui import get_spreadsheet_connection, init_page
=======
from utils.supabase_db import fetch_table, insert_record
from utils.ui import init_page
>>>>>>> Stashed changes
from utils.whatsapp_sender import generate_whatsapp_link

EMAIL_TYPE = "Promotional"
OPEN_LEAD_STATUSES = {"new", "contacted", "interested", "negotiation"}
TEMPLATES = {
    "New Stock Arrived": {
        "subject": "New Stock Available - {part_name} | Satyam Tex Fabb",
        "body": """Dear {customer_name},

We are pleased to inform you that we have received fresh stock of {part_name} at Satyam Tex Fabb.

Quantity Available: {quantity}
Price: Rs {price} per unit

This is a limited stock update and we recommend placing your order at the earliest to avoid delays.

For orders or enquiries, please contact us directly.

Warm regards,
Satyam Tex Fabb
Bhilwara, Rajasthan""",
    },
    "Festival Offer": {
        "subject": "Exclusive Festival Offer from Satyam Tex Fabb",
        "body": """Dear {customer_name},

Warm greetings from Satyam Tex Fabb!

On the occasion of {festival_name}, we are delighted to offer you a special discount of {discount}% on selected machinery parts.

Offer valid till: {valid_till}

We value your continued association with us and look forward to serving your machinery parts requirements.

For orders, please contact us at your earliest convenience.

Warm regards,
Satyam Tex Fabb
Bhilwara, Rajasthan""",
    },
    "Payment Follow-up": {
        "subject": "Friendly Follow-up - Outstanding Payment | Satyam Tex Fabb",
        "body": """Dear {customer_name},

Hope this message finds you well.

We would like to draw your attention to the outstanding payment of Rs {amount} against Invoice No. {invoice_number}, which was due on {due_date}.

We request you to kindly arrange the payment at your earliest convenience. If the payment has already been processed, please ignore this message.

For any queries, feel free to reach out to us.

Warm regards,
Satyam Tex Fabb
Bhilwara, Rajasthan""",
    },
    "New Product Launch": {
        "subject": "Introducing {product_name} - Now Available at Satyam Tex Fabb",
        "body": """Dear {customer_name},

We are excited to announce the availability of {product_name} at Satyam Tex Fabb.

{product_description}

As a valued customer, you get early access to this new addition to our inventory.

For pricing and availability, please contact us directly.

Warm regards,
Satyam Tex Fabb
Bhilwara, Rajasthan""",
    },
    "Service Announcement": {
        "subject": "Important Service Update from Satyam Tex Fabb",
        "body": """Dear {customer_name},

Greetings from Satyam Tex Fabb!

We would like to inform you about {announcement}.

{details}

We remain committed to providing you with the best quality machinery parts and service.

For further information, please do not hesitate to contact us.

Warm regards,
Satyam Tex Fabb
Bhilwara, Rajasthan""",
    },
    "Bulk Order Discount": {
        "subject": "Special Bulk Order Offer - Satyam Tex Fabb",
        "body": """Dear {customer_name},

Greetings from Satyam Tex Fabb!

We are pleased to offer you a special discount of {discount}% on bulk orders above {min_quantity} units of {part_name}.

This is a limited time offer valid till {valid_till}.

Place your order today and take advantage of this exclusive offer.

Warm regards,
Satyam Tex Fabb
Bhilwara, Rajasthan""",
    },
    "Custom Message": {
        "subject": "{subject}",
        "body": """{message}

Warm regards,
Satyam Tex Fabb
Bhilwara, Rajasthan""",
    },
}


init_page("Promotional Emails")
st.title("Promotional Emails")

<<<<<<< Updated upstream
spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

contacts_ws = get_or_create_worksheet(spreadsheet, CONTACTS_TAB, CONTACTS_HEADERS)
email_log_ws = get_or_create_worksheet(spreadsheet, EMAIL_LOG_TAB, EMAIL_LOG_HEADERS)

# Fetch directly from Supabase customers table; legacy alias "customers_leads" also resolves here
_raw_contacts = fetch_table("customers")
contacts = []
for rec in _raw_contacts:
    contacts.append({
        "Name": str(rec.get("name") or rec.get("Name") or "").strip(),
        "Business Name": str(rec.get("business_name") or rec.get("Business Name") or "").strip(),
        "Phone": str(rec.get("phone") or rec.get("Phone") or "").strip(),
        "Email": str(rec.get("email") or rec.get("Email") or "").strip(),
        "Machine Type": str(rec.get("machine_type") or rec.get("Machine Type") or "").strip(),
        "Lead Status": str(rec.get("lead_status") or rec.get("Lead Status") or "").strip(),
    })
=======
contacts = [c for c in (fetch_table("customers") or []) if c is not None]
>>>>>>> Stashed changes

audience_rows = []
for contact in contacts:
    email = str(contact.get("email") or "").strip()
    phone = str(contact.get("phone") or "").strip()
    if not email and not phone:
        continue

    audience_rows.append(
        {
            "Select": False,
            "Name": str(contact.get("name") or "").strip(),
            "name": str(contact.get("name") or "").strip(),
            "Business Name": str(contact.get("business_name") or "").strip(),
            "business_name": str(contact.get("business_name") or "").strip(),
            "Email": email,
            "email": email,
            "Phone": phone,
            "phone": phone,
            "Machine Type": str(contact.get("machine_type") or "").strip(),
            "Lead Status": str(contact.get("lead_status") or "").strip(),
        }
    )

if not audience_rows:
    if not _raw_contacts:
        st.warning(
            "No contacts found in the database. "
            "Add customers or leads via the **Customers & Leads** page first."
        )
    else:
        st.info(
            f"{len(_raw_contacts)} contact(s) found but none have a phone or email address. "
            "Update contact details in the **Customers & Leads** page."
        )
    st.stop()

all_df = pd.DataFrame(audience_rows)

st.subheader("📧 Email Template Composer")
template_name = st.selectbox("Select Template", options=list(TEMPLATES.keys()))
bulk_mode = st.checkbox("Compose for bulk recipients", value=True)
default_customer_name = "Valued Customer" if bulk_mode else "Valued Customer"

template_values = {"customer_name": default_customer_name}

if template_name == "New Stock Arrived":
    template_values["customer_name"] = st.text_input("Customer Name", value=default_customer_name)
    template_values["part_name"] = st.text_input("Part Name")
    template_values["quantity"] = st.text_input("Quantity")
    template_values["price"] = st.text_input("Price")
elif template_name == "Festival Offer":
    template_values["customer_name"] = st.text_input("Customer Name", value=default_customer_name)
    template_values["festival_name"] = st.text_input("Festival Name")
    template_values["discount"] = st.text_input("Discount (%)")
    template_values["valid_till"] = st.date_input("Valid Till").isoformat()
elif template_name == "Payment Follow-up":
    customer_options = ["Valued Customer"] + sorted(all_df["Name"].dropna().astype(str).unique().tolist())
    default_idx = 0
    if not bulk_mode and len(customer_options) > 1:
        default_idx = 1
    template_values["customer_name"] = st.selectbox(
        "Customer Name",
        options=customer_options,
        index=default_idx,
    )
    template_values["amount"] = st.text_input("Outstanding Amount")
    template_values["invoice_number"] = st.text_input("Invoice Number")
    template_values["due_date"] = st.date_input("Due Date").isoformat()
elif template_name == "New Product Launch":
    template_values["customer_name"] = st.text_input("Customer Name", value=default_customer_name)
    template_values["product_name"] = st.text_input("Product Name")
    template_values["product_description"] = st.text_area("Product Description", height=120)
elif template_name == "Service Announcement":
    template_values["customer_name"] = st.text_input("Customer Name", value=default_customer_name)
    template_values["announcement"] = st.text_input("Announcement Title")
    template_values["details"] = st.text_area("Details", height=120)
elif template_name == "Bulk Order Discount":
    template_values["customer_name"] = st.text_input("Customer Name", value=default_customer_name)
    template_values["part_name"] = st.text_input("Part Name")
    template_values["discount"] = st.text_input("Discount (%)")
    template_values["min_quantity"] = st.text_input("Minimum Quantity")
    template_values["valid_till"] = st.date_input("Valid Till", key="bulk_valid_till").isoformat()
elif template_name == "Custom Message":
    template_values["subject"] = st.text_input("Custom Subject")
    template_values["message"] = st.text_area("Message", height=150)

if st.button("Compose Email", type="primary"):
    selected_template = TEMPLATES[template_name]
    try:
        composed_subject = selected_template["subject"].format(**template_values)
        composed_body = selected_template["body"].format(**template_values)
        st.session_state["promo_subject"] = composed_subject.strip()
        st.session_state["promo_body"] = composed_body.strip()
        st.success("✅ Email composed! Scroll down to select recipients and send.")
        with st.expander("Preview Composed Email", expanded=True):
            st.markdown(f"**Subject:** {composed_subject}")
            st.text_area("Email Preview", value=composed_body, height=260, disabled=True)
    except KeyError as exc:
        st.error(f"Missing required field for template: {exc}")

st.markdown("---")

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
default_subject = st.session_state.get(
    "promo_subject",
    "Exclusive Update from Satyam Tex Fabb",
)
default_body = st.session_state.get(
    "promo_body",
    (
        "Dear [Customer Name],\n\n"
        "Greetings from Satyam Tex Fabb!\n\n"
        "[Custom message here]\n\n"
        "We value your continued association with us and look forward to serving your machinery parts requirements.\n\n"
        "For orders or enquiries, please contact us anytime.\n\n"
        "Warm regards,\n"
        "Satyam Tex Fabb\n"
        "Bhilwara, Rajasthan"
    ),
)
subject = st.text_input("Subject", value=default_subject)
body = st.text_area(
    "Email Body",
    value=default_body,
    height=260,
)

st.subheader("Preview")
preview_name = "Customer"
if not selected_df.empty:
    preview_name = selected_df.iloc[0]["Name"]
preview_body = body.replace("[Customer Name]", preview_name)
st.markdown(f"**Subject:** {subject}")
st.text_area("Preview Body", value=preview_body, height=220, disabled=True)


def personalize(text, row):
    result = text
    result = result.replace("[Customer Name]", str(row.get("name", "")))
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
        recipient_name = str(row.get("name", "")).strip()
        recipient_email = str(row.get("email", "")).strip()
        recipient_phone = str(row.get("phone", "")).strip()
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
                    insert_record(
                        "email_log",
                        {
                            "timestamp": timestamp,
                            "email_type": EMAIL_TYPE,
                            "recipient_name": recipient_name,
                            "recipient_email": recipient_email,
                            "subject": subject,
                            "status": "Sent",
                            "error": "",
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
                whatsapp_link = generate_whatsapp_link(recipient_phone, personalized_body)
                st.link_button("📲 Send via WhatsApp", whatsapp_link)
                whatsapp_status = "Link Ready"

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
