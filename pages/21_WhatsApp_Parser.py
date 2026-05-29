import re
from datetime import datetime

import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.supabase_db import fetch_table, get_supabase, insert_record

require_login()

st.set_page_config(page_title="WhatsApp Parser", page_icon="💬", layout="wide")
st.title("💬 WhatsApp Business Chat Parser")
st.caption("Upload WhatsApp Business .txt export → auto-parse → store to Supabase")


def parse_whatsapp_txt(text: str) -> list:
    fmt1 = re.compile(
        r'^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}(?::\d{2})?)\]\s*([^:]+?):\s*(.+)$'
    )
    fmt2 = re.compile(
        r'^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2})\s*-\s*([^:]+?):\s*(.+)$'
    )
    phone_re = re.compile(r'^\+?[\d\s\-()‪‬]{7,}$')
    skip_msgs = {"<media omitted>", "null", "this message was deleted"}
    skip_line = ["end-to-end encrypted", "messages and calls are"]

    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(s in line.lower() for s in skip_line):
            continue

        m = fmt1.match(line) or fmt2.match(line)
        if not m:
            continue

        date_str, time_str, sender, msg = m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip()

        if not sender or msg.lower() in skip_msgs:
            continue

        # Parse date
        try:
            parts = date_str.split("/")
            d, mo, yr = int(parts[0]), int(parts[1]), int(parts[2])
            if yr < 100:
                yr += 2000
            msg_date = datetime(yr, mo, d).date()
        except Exception:
            continue

        # Parse time
        try:
            t_parts = time_str.split(":")
            h, mi = int(t_parts[0]), int(t_parts[1])
            s = int(t_parts[2]) if len(t_parts) > 2 else 0
            msg_time = datetime(2000, 1, 1, h, mi, s).time()
        except Exception:
            continue

        # Phone or name
        if phone_re.match(sender):
            phone_number = sender
            sender_name = None
        else:
            phone_number = None
            sender_name = sender

        # Intent
        ml = msg.lower()
        if any(k in ml for k in ["order", "chahiye", "quantity", "kg", "piece", "pcs", "units", "nos"]):
            intent = "Order Inquiry"
        elif any(k in ml for k in ["price", "rate", "kitna", "cost", "quote", "quotation"]):
            intent = "Price Inquiry"
        elif any(k in ml for k in ["follow", "call back", "callback", "baat", "contact", "revert"]):
            intent = "Follow Up"
        elif any(k in ml for k in ["complaint", "problem", "issue", "kharab", "defect", "return", "wrong"]):
            intent = "Complaint"
        else:
            intent = "General"

        rows.append({
            "sender_name": sender_name,
            "phone_number": phone_number,
            "message_date": msg_date,
            "message_time": msg_time,
            "message_text": msg,
            "parsed_intent": intent,
            "raw_filename": None,
        })
    return rows


# ── UPLOAD ────────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload WhatsApp Business Chat Export (.txt)",
    type=["txt"],
    help="In WhatsApp Business: open chat → ⋮ → More → Export Chat → Without Media",
)

if uploaded_file:
    raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
    rows = parse_whatsapp_txt(raw_text)

    for row in rows:
        row["raw_filename"] = uploaded_file.name

    df = pd.DataFrame(rows)

    if len(df) == 0:
        st.warning("No messages parsed. Check file format — must be WhatsApp .txt export.")

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Messages", len(df))
    col2.metric("Unique Senders", df["sender_name"].nunique() if "sender_name" in df.columns else 0)
    col3.metric(
        "Date Range",
        f"{df['message_date'].min()} → {df['message_date'].max()}" if len(df) else "—",
    )
    col4.metric("Phone Numbers Found", df["phone_number"].notna().sum() if len(df) > 0 and "phone_number" in df.columns else 0)

    st.subheader("Intent Breakdown")
    intent_cols = st.columns(5)
    for i, intent in enumerate(["Order Inquiry", "Price Inquiry", "Follow Up", "Complaint", "General"]):
        count = len(df[df["parsed_intent"] == intent]) if "parsed_intent" in df.columns else 0
        intent_cols[i].metric(intent, count)

    st.subheader("Parsed Messages Preview")
    if len(df) > 0:
        st.dataframe(df, use_container_width=True, height=400)

    # ── SAVE ─────────────────────────────────────────────────────────────────
    if st.button("💾 Save to Supabase", type="primary"):
        success_count = 0
        errors = []
        for row in rows:
            row["raw_filename"] = uploaded_file.name
            row["message_date"] = str(row["message_date"]) if row["message_date"] else None
            row["message_time"] = str(row["message_time"]) if row["message_time"] else None
            try:
                insert_record("whatsapp_chats", row)
                success_count += 1
            except Exception as e:
                errors.append(str(e))

        if success_count:
            st.success(f"✅ {success_count} messages saved to Supabase")
        if errors:
            st.error(f"❌ {len(errors)} failed")
            with st.expander("Error details"):
                for e in errors:
                    st.write(e)

# ── VIEW SAVED RECORDS ────────────────────────────────────────────────────────
st.divider()
with st.expander("📋 View Saved Records from Supabase", expanded=False):
    data = fetch_table("whatsapp_chats")

    if data:
        df_saved = pd.DataFrame(data)

        fcol1, fcol2, _ = st.columns(3)
        sender_filter = fcol1.text_input("Filter by sender")
        intent_filter = fcol2.selectbox(
            "Filter by intent",
            ["All", "Order Inquiry", "Price Inquiry", "Follow Up", "Complaint", "General"],
        )

        if sender_filter:
            df_saved = df_saved[df_saved["sender_name"].str.contains(sender_filter, case=False, na=False)]
        if intent_filter != "All":
            df_saved = df_saved[df_saved["parsed_intent"] == intent_filter]

        st.dataframe(df_saved, use_container_width=True)

        csv = df_saved.to_csv(index=False)
        st.download_button("⬇️ Export as CSV", csv, "whatsapp_chats.csv", "text/csv")
    else:
        st.info("No saved records yet. Upload and save a chat file above.")
