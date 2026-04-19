import streamlit as st

if "username" not in st.session_state or not st.session_state.get("username"):
    st.warning("Please login first.")
    st.stop()

import pandas as pd

from utils.auth import is_admin, require_login
from utils.supabase_db import (
    SOFT_DELETE_TABLES,
    fetch_soft_deleted,
    hard_delete_record,
    restore_record,
)
from utils.ui import init_page

require_login()
init_page("Recycle Bin")
st.title("🗑️ Recycle Bin")

if not is_admin():
    st.error("Admin access required.")
    st.stop()

TABLE_LABELS = {
    "parts": "Parts",
    "customers": "Customers & Leads",
    "sales_records": "Sales Records",
    "purchase_records": "Purchase Records",
}
# Human-readable description per row, keyed by source table.
ROW_DESCRIBERS = {
    "parts": lambda r: f"{r.get('part_name') or '—'} · {r.get('category') or '—'} · qty {r.get('quantity') or 0}",
    "customers": lambda r: f"{r.get('name') or r.get('business_name') or '—'} · {r.get('phone') or '—'}",
    "sales_records": lambda r: f"{r.get('date','')} · {r.get('part_name') or '—'} → {r.get('party_name') or '—'} · ₹{r.get('total_sale_value') or 0}",
    "purchase_records": lambda r: f"{r.get('date','')} · {r.get('part_name') or '—'} ← {r.get('supplier_name') or '—'} · ₹{r.get('total_purchase_value') or 0}",
}

st.caption(
    "Rows soft-deleted via the app. **Restore** returns a row to the live data; "
    "**Delete forever** removes it permanently and cannot be undone."
)

# Quick summary across all four tables.
summary = {label: len(fetch_soft_deleted(t)) for t, label in TABLE_LABELS.items()}
total = sum(summary.values())
if total == 0:
    st.success("Recycle bin is empty.")
    st.stop()

cols = st.columns(len(summary))
for (label, count), col in zip(summary.items(), cols):
    col.metric(label, count)

st.markdown("---")

tabs = st.tabs([f"{label} ({summary[label]})" for label in TABLE_LABELS.values()])
for (table, label), tab in zip(TABLE_LABELS.items(), tabs):
    with tab:
        rows = fetch_soft_deleted(table)
        if not rows:
            st.info(f"No deleted {label.lower()}.")
            continue

        describe = ROW_DESCRIBERS[table]

        for row in rows:
            row_id = row.get("id")
            deleted_at = str(row.get("deleted_at") or "")[:19].replace("T", " ")
            with st.container(border=True):
                c1, c2, c3 = st.columns([5, 1, 1])
                with c1:
                    st.markdown(f"**{describe(row)}**")
                    st.caption(f"Deleted at {deleted_at} · id `{row_id}`")
                with c2:
                    if st.button("♻️ Restore", key=f"restore_{table}_{row_id}"):
                        if restore_record(table, "id", row_id) is not None:
                            st.success(f"Restored to {label}.")
                            st.rerun()
                with c3:
                    confirm_key = f"confirm_purge_{table}_{row_id}"
                    if st.session_state.get(confirm_key):
                        if st.button("🔥 Confirm", key=f"purge_{table}_{row_id}"):
                            if hard_delete_record(table, "id", row_id) is not None:
                                st.session_state.pop(confirm_key, None)
                                st.success("Permanently deleted.")
                                st.rerun()
                    else:
                        if st.button("🗑️ Delete forever", key=f"ask_purge_{table}_{row_id}"):
                            st.session_state[confirm_key] = True
                            st.rerun()

        with st.expander(f"View raw data for {label}"):
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
