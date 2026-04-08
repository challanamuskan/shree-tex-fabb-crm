from datetime import date, datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st

from utils.constants import PARTS_TAB, SETTINGS_HEADERS, SETTINGS_TAB
from utils.supabase_db import fetch_tab, get_or_create_worksheet
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
        import pandas as pd

        parts = fetch_tab("parts")
        if not parts:
            return False, "No parts data"

        df = pd.DataFrame(parts)

        def safe_int(v):
            try:
                return int(float(str(v).strip()))
            except:
                return 0

        df["_qty"] = df["Quantity"].apply(safe_int)
        df["_reorder"] = df.get("Reorder_Level", pd.Series([0] * len(df))).apply(safe_int)
        low = df[(df["_reorder"] > 0) & (df["_qty"] <= df["_reorder"])]

        if low.empty:
            return True, "No low stock items found"

        rows_html = ""
        for _, row in low.iterrows():
            rows_html += (
                f"<tr><td>{row.get('Category', '')}</td><td>{row.get('Part_Name', '')}</td>"
                f"<td>{row['_qty']}</td><td>{row['_reorder']}</td></tr>"
            )

        html = f"""
        <h2>⚠️ Low Stock Alert — Satyam Tex Fabb</h2>
        <p>Date: {date.today()}</p>
        <table border='1' cellpadding='6' style='border-collapse:collapse'>
        <tr><th>Category</th><th>Part Name</th><th>Current Stock</th><th>Reorder Level</th></tr>
        {rows_html}
        </table>
        """

        smtp_server = st.secrets.get("smtp_server", "smtp.gmail.com")
        smtp_port = int(st.secrets.get("smtp_port", 587))
        sender_email = st.secrets.get("sender_email", "")
        sender_password = st.secrets.get("sender_password", "")
        admin_email = st.secrets.get("admin_email", "")

        if not all([sender_email, sender_password, admin_email]):
            return False, "Email credentials not configured in secrets.toml"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"⚠️ Low Stock Alert — Satyam Tex Fabb {date.today()}"
        msg["From"] = sender_email
        msg["To"] = admin_email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, admin_email, msg.as_string())

        return True, f"Alert sent for {len(low)} low stock items"

    except Exception as e:
        return False, str(e)
