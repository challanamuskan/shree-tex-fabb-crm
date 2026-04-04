from datetime import date, datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st

from utils.constants import PARTS_TAB, SETTINGS_HEADERS, SETTINGS_TAB
from utils.sheets_db import fetch_tab, get_or_create_worksheet
from utils.ui import get_spreadsheet_connection


DEFAULT_ADMIN_EMAIL = ""
LOW_STOCK_SETTING_KEY = "low_stock_auto_alert"


def _to_int(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0


def _resolve_admin_email():
    try:
        configured = str(st.secrets.get("admin_email", "")).strip()
    except Exception:
        configured = ""
    return configured or DEFAULT_ADMIN_EMAIL


def _resolve_smtp_config():
    try:
        host = str(st.secrets.get("smtp_host", "smtp.gmail.com")).strip() or "smtp.gmail.com"
        port = int(st.secrets.get("smtp_port", 587))
        username = str(st.secrets.get("smtp_username", "")).strip()
        password = str(st.secrets.get("smtp_password", "")).strip()
        sender = str(st.secrets.get("smtp_sender", username)).strip() or username
        return host, port, username, password, sender
    except Exception:
        return "smtp.gmail.com", 587, "", "", ""


def get_low_stock_auto_alert_setting():
    try:
        records = fetch_tab(SETTINGS_TAB)
    except Exception:
        return False

    for record in records:
        if str(record.get("key", "")).strip() == LOW_STOCK_SETTING_KEY:
            value = str(record.get("value", "")).strip().lower()
            return value in {"true", "1", "yes", "on"}
    return False


def set_low_stock_auto_alert_setting(enabled):
    spreadsheet = get_spreadsheet_connection()
    if not spreadsheet:
        return False

    ws = get_or_create_worksheet(spreadsheet, SETTINGS_TAB, SETTINGS_HEADERS)
    key_column = ws.col_values(1)
    target_row = None
    for idx, key in enumerate(key_column, start=1):
        if idx == 1:
            continue
        if str(key).strip() == LOW_STOCK_SETTING_KEY:
            target_row = idx
            break

    value = "True" if enabled else "False"
    updated_at = datetime.now().isoformat(timespec="seconds")

    if target_row:
        ws.update(
            f"A{target_row}:C{target_row}",
            [[LOW_STOCK_SETTING_KEY, value, updated_at]],
            value_input_option="USER_ENTERED",
        )
    else:
        ws.append_row([LOW_STOCK_SETTING_KEY, value, updated_at], value_input_option="USER_ENTERED")

    st.cache_data.clear()
    return True


def send_low_stock_email_alert():
    try:
        parts = fetch_tab("Parts")
    except Exception:
        parts = []

    if not parts:
        try:
            parts = fetch_tab(PARTS_TAB)
        except Exception:
            parts = []

    low_stock_items = []
    for part in parts:
        quantity = _to_int(part.get("Quantity", 0))
        reorder_level = _to_int(part.get("Reorder_Level", 0))
        if reorder_level > 0 and quantity <= reorder_level:
            low_stock_items.append(
                {
                    "Part_Name": str(part.get("Part_Name", "")).strip(),
                    "Category": str(part.get("Category", "")).strip(),
                    "Quantity": quantity,
                    "Reorder_Level": reorder_level,
                }
            )

    if not low_stock_items:
        return True, 0, "No low stock items found."

    admin_email = _resolve_admin_email()
    if not admin_email:
        return False, 0, "Missing admin_email in Streamlit secrets."

    host, port, username, password, sender = _resolve_smtp_config()
    if not username or not password:
        return False, 0, "Missing SMTP credentials in Streamlit secrets."

    subject = f"⚠️ Low Stock Alert — Satyam Tex Fabb {date.today().isoformat()}"
    rows_html = "".join(
        [
            "<tr>"
            f"<td>{item['Part_Name']}</td>"
            f"<td>{item['Category']}</td>"
            f"<td>{item['Quantity']}</td>"
            f"<td>{item['Reorder_Level']}</td>"
            "</tr>"
            for item in low_stock_items
        ]
    )
    body_html = (
        "<html><body>"
        "<p>The following items are at or below reorder level:</p>"
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<tr><th>Part Name</th><th>Category</th><th>Current Stock</th><th>Reorder Level</th></tr>"
        f"{rows_html}"
        "</table>"
        "</body></html>"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = admin_email
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls()
            server.login(username, password)
            server.sendmail(sender, [admin_email], msg.as_string())
        return True, len(low_stock_items), "Low stock alert email sent."
    except Exception as exc:
        return False, 0, str(exc)
