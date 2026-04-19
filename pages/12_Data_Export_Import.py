"""Per-table CSV/Excel export + import with fuzzy column mapping."""
import difflib
import io
import re
from datetime import date

import pandas as pd
import streamlit as st

if "username" not in st.session_state or not st.session_state.get("username"):
    st.warning("Please login first.")
    st.stop()

from utils.auth import is_admin, require_login
from utils.supabase_db import _invalidate_cache, fetch_table, get_supabase
from utils.ui import init_page

require_login()
init_page("Data Export & Import")
st.title("📤 Data Export & Import")


# ─────────────────────────────────────────────────────────────────
# Per-table schema
#   columns:  ordered DB column names (what rows will be written as)
#   required: subset that must have a non-empty value on import
#   aliases:  non-standard source-column names the fuzzy matcher
#             cannot reach on its own (Tally/legacy abbreviations)
#   date_col: enables the date-range filter on export; None = no filter
# ─────────────────────────────────────────────────────────────────
TABLE_SCHEMA = {
    "parts": {
        "label": "Parts (Stock)",
        "columns": [
            "cid", "category", "part_name", "unit_sale_price", "quantity",
            "status", "date_added", "legacy_id", "price_type", "box_number",
            "supplier_name", "image_url",
        ],
        "required": ["part_name"],
        "aliases": {
            "category": ["cname", "cat", "category_name"],
            "part_name": ["productname", "product_name", "item_name", "product"],
            "unit_sale_price": ["price", "sale_price", "rate", "mrp"],
            "quantity": ["balance", "qty", "stock", "in_stock"],
            "date_added": ["balancedate", "added_on"],
            "legacy_id": ["item_id", "old_id", "ref_id"],
            "price_type": ["pricetype"],
            "supplier_name": ["clientname", "client_name", "supplier", "vendor", "vendor_name"],
            "box_number": ["boxnumber", "box", "bin"],
        },
        "date_col": None,
    },
    "customers": {
        "label": "Customers & Leads",
        "columns": [
            "name", "business_name", "phone", "email", "machine_type",
            "lead_status", "follow_up_date", "notes",
        ],
        "required": ["name"],
        "aliases": {
            "name": ["contact_name", "customer_name", "full_name", "party"],
            "business_name": ["company", "firm", "business"],
            "phone": ["mobile", "contact", "cell", "mobile_no", "phone_number"],
            "email": ["email_id", "mail"],
            "lead_status": ["status", "stage"],
            "follow_up_date": ["followup", "next_contact", "follow_up"],
        },
        "date_col": None,
    },
    "sales_records": {
        "label": "Sales Records",
        "columns": [
            "date", "part_name", "category", "supplier", "quantity_sold",
            "sale_invoice_number", "party_name", "sale_price_per_unit",
            "total_sale_value",
        ],
        "required": ["date", "part_name"],
        "aliases": {
            "date": ["sale_date", "invoice_date"],
            "part_name": ["product", "item", "product_name"],
            "quantity_sold": ["qty", "quantity", "nos", "units"],
            "sale_invoice_number": ["invoice", "invoice_no", "inv_no", "bill_no"],
            "party_name": ["customer", "buyer", "client"],
            "sale_price_per_unit": ["unit_price", "rate", "price"],
            "total_sale_value": ["amount", "total", "grand_total"],
        },
        "date_col": "date",
    },
    "purchase_records": {
        "label": "Purchase Records",
        "columns": [
            "date", "part_name", "category", "supplier_name",
            "quantity_purchased", "purchase_invoice_number",
            "purchase_price_per_unit", "total_purchase_value",
        ],
        "required": ["date", "part_name"],
        "aliases": {
            "date": ["purchase_date", "bill_date", "invoice_date"],
            "part_name": ["product", "item", "product_name"],
            "supplier_name": ["supplier", "vendor", "from", "vendor_name"],
            "quantity_purchased": ["qty", "quantity", "nos", "units"],
            "purchase_invoice_number": ["invoice", "invoice_no", "inv_no", "bill_no"],
            "purchase_price_per_unit": ["unit_price", "rate", "price"],
            "total_purchase_value": ["amount", "total", "grand_total"],
        },
        "date_col": "date",
    },
    "returns": {
        "label": "Returns",
        "columns": [
            "date", "type", "part_name", "quantity", "invoice_number",
            "party_supplier_name", "reason", "return_document", "category",
            "supplier_name",
        ],
        "required": [],  # export-only
        "aliases": {},
        "date_col": "date",
    },
}

EXPORT_TABLES = list(TABLE_SCHEMA.keys())
IMPORT_TABLES = ["parts", "customers", "sales_records", "purchase_records"]


# ─────────────────────────────────────────────────────────────────
# Fuzzy column mapping
# ─────────────────────────────────────────────────────────────────
def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def auto_map_columns(target_cols, aliases, source_cols):
    """For each target DB column, pick the best-matching source column.
    Priority: exact normalized match → alias match → substring containment
    → difflib similarity ≥ 0.75. Returns {target: source_col or None}."""
    source_by_norm = {_norm(c): c for c in source_cols if _norm(c)}
    mapping = {}
    for tgt in target_cols:
        tgt_n = _norm(tgt)

        if tgt_n in source_by_norm:
            mapping[tgt] = source_by_norm[tgt_n]
            continue

        aliased = None
        for alias in aliases.get(tgt, []):
            a_n = _norm(alias)
            if a_n in source_by_norm:
                aliased = source_by_norm[a_n]
                break
        if aliased:
            mapping[tgt] = aliased
            continue

        best, best_score = None, 0.0
        for sn, orig in source_by_norm.items():
            if tgt_n and (tgt_n in sn or sn in tgt_n):
                score = 0.85
            else:
                score = difflib.SequenceMatcher(None, tgt_n, sn).ratio()
            if score > best_score:
                best_score, best = score, orig
        mapping[tgt] = best if best_score >= 0.75 else None
    return mapping


def parse_upload(upload):
    name = upload.name.lower()
    data = upload.getvalue()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
    if name.endswith(".xls"):
        try:
            return pd.read_excel(io.BytesIO(data), engine="xlrd", dtype=str)
        except Exception:
            return pd.read_excel(io.BytesIO(data), engine="openpyxl", dtype=str)
    if name.endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(data), engine="openpyxl", dtype=str)
    raise ValueError("Unsupported file type — use CSV, XLS, or XLSX.")


# ─────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────
st.subheader("Section A — Export")

export_choice = st.selectbox(
    "Table to export",
    options=EXPORT_TABLES,
    format_func=lambda t: f"{TABLE_SCHEMA[t]['label']}  ·  {t}",
    key="exp_tbl",
)
export_format = st.radio("Format", ["CSV", "Excel (.xlsx)"], horizontal=True, key="exp_fmt")

exp_schema = TABLE_SCHEMA[export_choice]
date_start, date_end = None, None
if exp_schema["date_col"]:
    use_range = st.checkbox("Filter by date range", key="exp_date_on")
    if use_range:
        c1, c2 = st.columns(2)
        date_start = c1.date_input("From", value=date.today().replace(day=1), key="exp_start")
        date_end = c2.date_input("To", value=date.today(), key="exp_end")

if st.button("Generate export", type="primary"):
    with st.spinner(f"Fetching {export_choice}…"):
        rows = fetch_table(export_choice)
    df = pd.DataFrame(rows)

    if df.empty:
        st.warning(f"No rows in {export_choice}.")
    else:
        # Drop internal/soft-delete columns before export
        df = df.drop(columns=[c for c in ["deleted_at"] if c in df.columns])

        if date_start and date_end and exp_schema["date_col"] in df.columns:
            parsed = pd.to_datetime(df[exp_schema["date_col"]], errors="coerce").dt.date
            df = df[(parsed >= date_start) & (parsed <= date_end)]

        # Reorder: id first, then schema columns in order, then any extras
        ordered = [c for c in exp_schema["columns"] if c in df.columns]
        extras = [c for c in df.columns if c not in ordered and c != "id"]
        final_cols = (["id"] if "id" in df.columns else []) + ordered + extras
        df = df[final_cols]

        fname_base = f"{export_choice}_{date.today().isoformat()}"
        if export_format == "CSV":
            blob = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Download CSV",
                data=blob,
                file_name=f"{fname_base}.csv",
                mime="text/csv",
            )
        else:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                df.to_excel(writer, sheet_name=export_choice[:31], index=False)
            st.download_button(
                "⬇ Download Excel",
                data=buf.getvalue(),
                file_name=f"{fname_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        st.success(f"Ready: {len(df)} rows.")
        with st.expander("Preview (first 10 rows)"):
            st.dataframe(df.head(10), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Section B — Import")

if not is_admin():
    st.info("Import is available to admin users only.")
else:
    import_choice = st.selectbox(
        "Target table",
        options=IMPORT_TABLES,
        format_func=lambda t: f"{TABLE_SCHEMA[t]['label']}  ·  {t}",
        key="imp_tbl",
    )
    imp_schema = TABLE_SCHEMA[import_choice]
    upload = st.file_uploader("Upload CSV, XLSX, or XLS", type=["csv", "xlsx", "xls"], key=f"imp_file_{import_choice}")

    if upload is not None:
        try:
            raw_df = parse_upload(upload)
        except Exception as e:
            st.error(f"Could not read file: {e}")
            st.stop()

        raw_df.columns = [str(c).strip() for c in raw_df.columns]
        raw_df = raw_df.fillna("").astype(str)
        source_cols = list(raw_df.columns)
        st.success(f"✅ {len(raw_df)} rows loaded · {len(source_cols)} source columns")

        auto_map = auto_map_columns(imp_schema["columns"], imp_schema["aliases"], source_cols)

        st.markdown("### 🔗 Column mapping")
        st.caption(
            "Auto-detected — review and fix anything wrong. Pick **(skip)** to leave a column blank. "
            "★ = required; the import button stays disabled until required columns are mapped."
        )

        final_map = {}
        n_auto = sum(1 for v in auto_map.values() if v)
        st.caption(f"Auto-mapped {n_auto} of {len(imp_schema['columns'])} target columns.")

        map_cols = st.columns(2)
        for i, tgt in enumerate(imp_schema["columns"]):
            with map_cols[i % 2]:
                is_req = tgt in imp_schema["required"]
                label = f"**{tgt}**" + ("  ★" if is_req else "")
                options = ["(skip)"] + source_cols
                auto = auto_map.get(tgt)
                default_idx = options.index(auto) if auto in options else 0
                picked = st.selectbox(
                    label,
                    options=options,
                    index=default_idx,
                    key=f"map_{import_choice}_{tgt}",
                )
                final_map[tgt] = None if picked == "(skip)" else picked

        st.markdown("### 👀 Preview (first 5 rows, mapped)")
        preview_rows = []
        for idx in range(min(5, len(raw_df))):
            row = raw_df.iloc[idx]
            preview_rows.append({tgt: (row[src] if src else "") for tgt, src in final_map.items()})
        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

        missing_required = [t for t in imp_schema["required"] if not final_map.get(t)]
        if missing_required:
            st.error(f"Required columns not mapped: **{', '.join(missing_required)}**")

        unmapped = [t for t in imp_schema["columns"] if not final_map.get(t) and t not in imp_schema["required"]]
        if unmapped:
            st.caption(f"Unmapped (will be left blank): {', '.join(unmapped)}")

        can_import = not missing_required
        if st.button(
            f"⬆ Import {len(raw_df)} rows into {import_choice}",
            disabled=not can_import,
            type="primary",
            use_container_width=True,
        ):
            sb = get_supabase()
            progress = st.progress(0.0)
            status = st.empty()
            succeeded = 0
            failures = []  # (spreadsheet_row_no, error)

            for idx in range(len(raw_df)):
                row = raw_df.iloc[idx]
                payload = {}
                for tgt, src in final_map.items():
                    if not src:
                        continue
                    val = str(row[src] or "").strip()
                    if val:
                        payload[tgt] = val

                missing_in_row = [t for t in imp_schema["required"] if not payload.get(t)]
                if missing_in_row:
                    failures.append((idx + 2, f"Missing required: {', '.join(missing_in_row)}"))
                elif not payload:
                    failures.append((idx + 2, "Row is empty"))
                else:
                    try:
                        sb.table(import_choice).insert(payload).execute()
                        succeeded += 1
                    except Exception as e:
                        msg = str(e)
                        failures.append((idx + 2, msg[:250] + ("…" if len(msg) > 250 else "")))

                if (idx + 1) % 10 == 0 or idx == len(raw_df) - 1:
                    progress.progress((idx + 1) / max(1, len(raw_df)))
                    status.info(f"Processing… {idx + 1}/{len(raw_df)}  ·  ✅ {succeeded}  ·  ❌ {len(failures)}")

            _invalidate_cache(import_choice)
            progress.empty()
            status.empty()

            m1, m2 = st.columns(2)
            m1.metric("✅ Inserted", succeeded)
            m2.metric("❌ Failed", len(failures))

            if succeeded and not failures:
                st.success(f"All {succeeded} rows imported.")
                st.balloons()
            elif succeeded:
                st.warning(f"{succeeded} rows inserted, {len(failures)} failed — see table below.")
            else:
                st.error("No rows were inserted.")

            if failures:
                fail_df = pd.DataFrame(failures, columns=["Row #", "Error"])
                with st.expander(f"Failed rows ({len(failures)})", expanded=True):
                    st.dataframe(fail_df, use_container_width=True, hide_index=True)
                    st.download_button(
                        "⬇ Download failure report (CSV)",
                        data=fail_df.to_csv(index=False).encode("utf-8"),
                        file_name=f"{import_choice}_import_failures_{date.today().isoformat()}.csv",
                        mime="text/csv",
                    )


# ─────────────────────────────────────────────────────────────────
# Tally guide
# ─────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📘 Tally export guide"):
    st.markdown(
        """
1. Open Tally → Gateway of Tally
2. **Stock Summary** → `Alt+E` → Excel format → upload as **Parts (Stock)**
3. **Sales Register** → `Alt+E` → Excel format → upload as **Sales Records**
4. **Purchase Register** → `Alt+E` → Excel format → upload as **Purchase Records**

Column headers don't need to match exactly — common Tally and legacy export names
(e.g. `cname`, `productname`, `clientname`, `balance`, `balancedate`) are
recognised automatically. Anything unmapped can be fixed with the selectboxes above.
"""
    )
