import streamlit as st

if "username" not in st.session_state or not st.session_state.get("username"):
    st.warning("Please login first.")
    st.stop()

import pandas as pd

from utils.auth import is_admin, require_login
from utils.supabase_db import fetch_soft_deleted, hard_delete_record, restore_record
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

ROW_DESCRIBERS = {
    "parts": lambda r: (
        f"{r.get('part_name') or '—'} · {r.get('category') or '—'} · qty {r.get('quantity') or 0}"
    ),
    "customers": lambda r: (
        f"{r.get('name') or r.get('business_name') or '—'} · {r.get('phone') or '—'}"
    ),
    "sales_records": lambda r: (
        f"{r.get('date', '')} · {r.get('part_name') or '—'} → "
        f"{r.get('party_name') or '—'} · ₹{r.get('total_sale_value') or 0}"
    ),
    "purchase_records": lambda r: (
        f"{r.get('date', '')} · {r.get('part_name') or '—'} ← "
        f"{r.get('supplier_name') or '—'} · ₹{r.get('total_purchase_value') or 0}"
    ),
}

st.caption(
    "Rows soft-deleted via the app. **Restore** returns a row to live data; "
    "**Delete forever** removes it permanently and cannot be undone."
)

# ── Fetch ALL soft-deleted rows once, before any rendering ──────────
bin_data: dict[str, list] = {
    table: fetch_soft_deleted(table) for table in TABLE_LABELS
}
total = sum(len(rows) for rows in bin_data.values())

if total == 0:
    st.success("Recycle bin is empty.")
    st.stop()

# ── Summary metrics ──────────────────────────────────────────────────
metric_cols = st.columns(len(TABLE_LABELS))
for col, (table, label) in zip(metric_cols, TABLE_LABELS.items()):
    col.metric(label, len(bin_data[table]))

st.markdown("---")

# ── One tab per table ────────────────────────────────────────────────
tab_labels = [
    f"{label} ({len(bin_data[table])})"
    for table, label in TABLE_LABELS.items()
]
tabs = st.tabs(tab_labels)

for tab, (table, label) in zip(tabs, TABLE_LABELS.items()):
    rows = bin_data[table]
    with tab:
        if not rows:
            st.info(f"No deleted {label.lower()}.")
        else:
            describe = ROW_DESCRIBERS[table]

            for row in rows:
                row_id = row.get("id")
                deleted_at = str(row.get("deleted_at") or "")[:19].replace("T", " ")
                with st.container(border=True):
                    c_info, c_restore, c_delete = st.columns([5, 1, 1])
                    with c_info:
                        st.markdown(f"**{describe(row)}**")
                        st.caption(f"Deleted {deleted_at} · `{row_id}`")
                    with c_restore:
                        if st.button("♻️", key=f"restore_{table}_{row_id}", help="Restore"):
                            result = restore_record(table, "id", row_id)
                            if result is not None:
                                st.toast(f"Restored to {label}.", icon="♻️")
                                st.rerun()
                            else:
                                st.error("Restore failed.")
                    with c_delete:
                        confirm_key = f"_confirm_purge_{table}_{row_id}"
                        if st.session_state.get(confirm_key):
                            if st.button(
                                "✅ Yes, delete",
                                key=f"purge_{table}_{row_id}",
                                type="primary",
                            ):
                                result = hard_delete_record(table, "id", row_id)
                                if result is not None:
                                    st.session_state.pop(confirm_key, None)
                                    st.toast("Permanently deleted.", icon="🗑️")
                                    st.rerun()
                                else:
                                    st.error("Delete failed.")
                        else:
                            if st.button(
                                "🗑️",
                                key=f"ask_purge_{table}_{row_id}",
                                help="Delete forever",
                            ):
                                st.session_state[confirm_key] = True
                                st.rerun()

            with st.expander(f"Raw data ({len(rows)} rows)"):
                st.dataframe(
                    pd.DataFrame(rows).drop(columns=["deleted_at"], errors="ignore"),
                    use_container_width=True,
                    hide_index=True,
                )
