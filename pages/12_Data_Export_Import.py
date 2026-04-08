import io
import csv
import time
from datetime import date

from gspread.exceptions import APIError
import pandas as pd
import streamlit as st
from openpyxl import Workbook

from utils.auth import is_admin, require_login
from utils.constants import (
    CATEGORIES_HEADERS,
    CATEGORIES_TAB,
    CONTACTS_HEADERS,
    CONTACTS_TAB,
    PARTS_HEADERS,
    PARTS_TAB,
    PAYMENTS_HEADERS,
    PAYMENTS_TAB,
    PRICE_HISTORY_HEADERS,
    PRICE_HISTORY_TAB,
    PURCHASE_RECORDS_HEADERS,
    PURCHASE_RECORDS_TAB,
    RETURNS_HEADERS,
    RETURNS_TAB,
    SALES_RECORDS_HEADERS,
    SALES_RECORDS_TAB,
)
from utils.supabase_db import bulk_append_records, fetch_sheet_data_by_name, fetch_tab, get_or_create_worksheet
from utils.ui import get_spreadsheet_connection, init_page

require_login()
init_page("Data Export & Import")
st.title("📤 Data Export & Import")


def to_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def records_to_df(records):
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).drop(columns=["_row"], errors="ignore")


def make_excel(sheet_data):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        for name, df in sheet_data.items():
            safe_name = name[:31] if name else "Sheet"
            df.to_excel(writer, sheet_name=safe_name, index=False)
    buffer.seek(0)
    return buffer.getvalue()


def make_csv_combined(sheet_data):
    rows = []
    for sheet_name, df in sheet_data.items():
        if df.empty:
            continue
        temp = df.copy()
        temp["Sheet_Name"] = sheet_name
        rows.append(temp)
    if rows:
        out = pd.concat(rows, ignore_index=True)
    else:
        out = pd.DataFrame(columns=["Sheet_Name"])
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(out.columns.tolist())
    for row in out.itertuples(index=False):
        writer.writerow(list(row))
    return buffer.getvalue().encode("utf-8")


def make_excel_report(title, lines, sheet_data):
    buffer = io.BytesIO()
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append([title])
    summary.append([])
    for line in lines:
        summary.append([line])

    for sheet_name, df in sheet_data.items():
        worksheet = workbook.create_sheet(title=sheet_name[:31] if sheet_name else "Sheet")
        if df.empty:
            worksheet.append(["No data"])
            continue
        worksheet.append(list(df.columns))
        for row in df.itertuples(index=False):
            worksheet.append(list(row))

    workbook.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

st.subheader("Section A - Export Data")
export_type = st.selectbox(
    "Choose export option",
    ["Export Stock Data", "Export Transaction Data", "Export Full Backup"],
)
export_format = st.selectbox("Format", ["Excel", "CSV", "Excel report"])

if "export_blob" not in st.session_state:
    st.session_state["export_blob"] = None
    st.session_state["export_filename"] = ""
    st.session_state["export_button_text"] = "Download Export"

if export_type == "Export Transaction Data":
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", value=date.today(), key="txn_start")
    with c2:
        end_date = st.date_input("End Date", value=date.today(), key="txn_end")
else:
    start_date = None
    end_date = None

if st.button("Generate Export File"):
    with st.spinner("Fetching data from Google Sheets..."):
        if export_type == "Export Stock Data":
            parts = fetch_sheet_data_by_name(PARTS_TAB, PARTS_HEADERS)
            categories = fetch_sheet_data_by_name(CATEGORIES_TAB, CATEGORIES_HEADERS)
            price_history = fetch_sheet_data_by_name(PRICE_HISTORY_TAB, PRICE_HISTORY_HEADERS)

            stock_sheets = {
                PARTS_TAB: records_to_df(parts),
                PRICE_HISTORY_TAB: records_to_df(price_history),
                CATEGORIES_TAB: records_to_df(categories),
            }

            if export_format == "Excel":
                st.session_state["export_blob"] = make_excel(stock_sheets)
                st.session_state["export_filename"] = f"stock_data_{date.today().isoformat()}.xlsx"
                st.session_state["export_button_text"] = "Download Stock Excel"
            elif export_format == "CSV":
                st.session_state["export_blob"] = make_csv_combined(stock_sheets)
                st.session_state["export_filename"] = f"stock_data_{date.today().isoformat()}.csv"
                st.session_state["export_button_text"] = "Download Stock CSV"
            else:
                total_qty = sum(int(float(str(r.get("Quantity", "0") or 0))) for r in parts)
                lines = [
                    f"Stock rows: {len(parts)}",
                    f"Total quantity across suppliers: {total_qty}",
                    f"Categories: {len(categories)}",
                    f"Price history records: {len(price_history)}",
                ]
                st.session_state["export_blob"] = make_excel_report("Stock Summary Report", lines, stock_sheets)
                st.session_state["export_filename"] = f"stock_summary_{date.today().isoformat()}.xlsx"
                st.session_state["export_button_text"] = "Download Stock Excel Report"

        elif export_type == "Export Transaction Data":
            sales = fetch_sheet_data_by_name(SALES_RECORDS_TAB, SALES_RECORDS_HEADERS)
            purchases = fetch_sheet_data_by_name(PURCHASE_RECORDS_TAB, PURCHASE_RECORDS_HEADERS)
            returns = fetch_sheet_data_by_name(RETURNS_TAB, RETURNS_HEADERS)

            sales_df = records_to_df(sales)
            purchases_df = records_to_df(purchases)
            returns_df = records_to_df(returns)

            if not sales_df.empty:
                sales_df["Date"] = pd.to_datetime(sales_df["Date"], errors="coerce")
                sales_df = sales_df[(sales_df["Date"].dt.date >= start_date) & (sales_df["Date"].dt.date <= end_date)]
            if not purchases_df.empty:
                purchases_df["Date"] = pd.to_datetime(purchases_df["Date"], errors="coerce")
                purchases_df = purchases_df[(purchases_df["Date"].dt.date >= start_date) & (purchases_df["Date"].dt.date <= end_date)]
            if not returns_df.empty:
                returns_df["Date"] = pd.to_datetime(returns_df["Date"], errors="coerce")
                returns_df = returns_df[(returns_df["Date"].dt.date >= start_date) & (returns_df["Date"].dt.date <= end_date)]

            total_sales_value = pd.to_numeric(sales_df.get("Total_Sale_Value", 0), errors="coerce").fillna(0).sum() if not sales_df.empty else 0.0
            total_purchase_value = pd.to_numeric(purchases_df.get("Total_Purchase_Value", 0), errors="coerce").fillna(0).sum() if not purchases_df.empty else 0.0
            net_movement = total_sales_value - total_purchase_value
            st.markdown(
                f"Total sales value: Rs {total_sales_value:,.2f} | Total purchase value: Rs {total_purchase_value:,.2f} | Net movement: Rs {net_movement:,.2f}"
            )

            tx_sheets = {
                SALES_RECORDS_TAB: sales_df,
                PURCHASE_RECORDS_TAB: purchases_df,
                RETURNS_TAB: returns_df,
            }

            if export_format == "Excel":
                st.session_state["export_blob"] = make_excel(tx_sheets)
                st.session_state["export_filename"] = f"transactions_{date.today().isoformat()}.xlsx"
                st.session_state["export_button_text"] = "Download Transaction Excel"
            elif export_format == "CSV":
                st.session_state["export_blob"] = make_csv_combined(tx_sheets)
                st.session_state["export_filename"] = f"transactions_{date.today().isoformat()}.csv"
                st.session_state["export_button_text"] = "Download Transaction CSV"
            else:
                lines = [
                    f"Date range: {start_date} to {end_date}",
                    f"Sales rows: {len(sales_df)}",
                    f"Purchase rows: {len(purchases_df)}",
                    f"Return rows: {len(returns_df)}",
                    f"Total sales value: Rs {total_sales_value:,.2f}",
                    f"Total purchase value: Rs {total_purchase_value:,.2f}",
                    f"Net movement: Rs {net_movement:,.2f}",
                ]
                st.session_state["export_blob"] = make_excel_report("Transaction Summary Report", lines, tx_sheets)
                st.session_state["export_filename"] = f"transactions_{date.today().isoformat()}.xlsx"
                st.session_state["export_button_text"] = "Download Transaction Excel Report"

        else:
            all_sheets = {}
            for ws in spreadsheet.worksheets():
                records = fetch_tab(ws.title)
                all_sheets[ws.title] = pd.DataFrame(records)

            st.session_state["export_blob"] = make_excel(all_sheets)
            st.session_state["export_filename"] = f"Satyam_Tex_Fabb_Backup_{date.today().isoformat()}.xlsx"
            st.session_state["export_button_text"] = "Download Full Backup"

if st.session_state.get("export_blob"):
    st.download_button(
        st.session_state.get("export_button_text", "Download Export"),
        data=st.session_state["export_blob"],
        file_name=st.session_state.get("export_filename", f"export_{date.today().isoformat()}.xlsx"),
    )

st.markdown("---")
st.subheader("Section B - Import Data")
if not is_admin():
    st.info("Import is available for admin users only.")
else:
    upload = st.file_uploader("Upload file", type=["xlsx", "xls", "csv", "pdf"], key="import_file")

    target_sheet_options = {
        "Parts (Stock)": (PARTS_TAB, PARTS_HEADERS),
        "Customers": (CONTACTS_TAB, CONTACTS_HEADERS),
        "Sales_Records": (SALES_RECORDS_TAB, SALES_RECORDS_HEADERS),
        "Purchase_Records": (PURCHASE_RECORDS_TAB, PURCHASE_RECORDS_HEADERS),
        "Payments": (PAYMENTS_TAB, PAYMENTS_HEADERS),
    }
    target_name = st.selectbox("Import into", options=list(target_sheet_options.keys()), index=0)

    if upload is not None:
        file_bytes = upload.read()
        file_name = upload.name.lower()

        if file_name.endswith(".pdf"):
            st.warning("PDF import is not supported for data tables. Please convert to Excel first.")
            st.stop()

        try:
            if file_name.endswith(".csv"):
                input_df = pd.read_csv(io.BytesIO(file_bytes))
            elif file_name.endswith(".xls"):
                # Try xlrd first, fall back to openpyxl
                try:
                    input_df = pd.read_excel(io.BytesIO(file_bytes), engine="xlrd")
                except Exception:
                    try:
                        input_df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
                    except Exception:
                        # Last resort: save to temp file and read
                        import tempfile
                        import os

                        with tempfile.NamedTemporaryFile(delete=False, suffix=".xls") as tmp:
                            tmp.write(file_bytes)
                            tmp_path = tmp.name
                        input_df = pd.read_excel(tmp_path)
                        os.unlink(tmp_path)
            elif file_name.endswith(".xlsx"):
                input_df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
            else:
                st.error("Unsupported file type. Please upload .xls, .xlsx, or .csv")
                st.stop()

            st.success(f"✅ File loaded: {len(input_df)} rows")

        except Exception as e:
            st.error(f"Could not read file: {str(e)}")
            st.info("💡 Try saving your .xls file as .xlsx in Excel: File → Save As → Excel Workbook (.xlsx)")
            st.stop()

        if target_name == "Parts (Stock)":
            st.markdown("### 📥 Import Stock from Legacy Excel")
            input_df.columns = input_df.columns.str.strip()
            COLUMN_MAP = {
                "cid": "cid",
                "cname": "Category",
                "productname": "Part_Name",
                "price": "Unit_Sale_Price",
                "balance": "Quantity",
                "status": "status",
                "balancedate": "Date_Added",
                "id": "Legacy_ID",
                "pricetype": "Price_Type",
                "clientname": "Supplier_Name",
                "boxnumber": "Box_Number",
            }

            input_df = input_df.rename(columns=COLUMN_MAP)

            # Drop columns we don't need
            for col in ["image", "rts"]:
                if col in input_df.columns:
                    input_df = input_df.drop(columns=[col])

            if "Unit_Sale_Price" in input_df.columns:
                def clean_price(val):
                    try:
                        s = str(val).strip()
                        if s in ["", "nan", "None"]:
                            return ""
                        if "/" in s:
                            # Keep the last value after "/"
                            return s.split("/")[-1].strip()
                        return s
                    except:
                        return ""

                input_df["Unit_Sale_Price"] = input_df["Unit_Sale_Price"].apply(clean_price)

            PARTS_HEADERS = [
                "cid",
                "Category",
                "Part_Name",
                "Unit_Sale_Price",
                "Quantity",
                "status",
                "Date_Added",
                "Legacy_ID",
                "Price_Type",
                "Box_Number",
                "Supplier_Name",
            ]

            for col in PARTS_HEADERS:
                if col not in input_df.columns:
                    input_df[col] = ""

            df = input_df[PARTS_HEADERS]
            df = df.fillna("").astype(str)
            # Replace "nan" strings with empty string
            df = df.replace("nan", "").replace("None", "")

            st.subheader("📋 Preview (first 5 rows)")
            st.dataframe(df.head(5), use_container_width=True, hide_index=True)
            st.metric("Total rows ready to import", len(df))
            st.metric("Columns detected", ", ".join(df.columns.tolist()))

            import_btn = st.button(
                f"⬆️ Import All {len(df)} Rows → Parts (Stock)",
                type="primary",
                use_container_width=True,
            )

            if import_btn:
                CHUNK_SIZE = 400
                chunks = [df[i : i + CHUNK_SIZE] for i in range(0, len(df), CHUNK_SIZE)]
                progress = st.progress(0)
                status = st.empty()
                total_imported = 0

                sh = get_spreadsheet_connection()
                ws = sh.worksheet("Parts")

                for i, chunk in enumerate(chunks):
                    try:
                        chunk_clean = chunk.fillna("").astype(str)
                        rows = chunk_clean.values.tolist()
                        ws.append_rows(rows, value_input_option="USER_ENTERED")
                        total_imported += len(rows)
                        progress.progress((i + 1) / len(chunks))
                        status.info(f"Importing... {total_imported}/{len(df)} rows done")
                        time.sleep(2)
                    except Exception as e:
                        st.error(f"Import stopped at row {total_imported}: {str(e)}")
                        st.warning(f"✅ {total_imported} rows were saved. Wait 2 mins and re-upload to continue.")
                        st.stop()

                st.cache_data.clear()
                st.success(f"✅ All {total_imported} rows imported successfully!")
                st.balloons()
        else:
            target_tab, target_headers = target_sheet_options[target_name]
            working_df = input_df.copy()
            for header in target_headers:
                if header not in working_df.columns:
                    working_df[header] = ""

            ordered_df = working_df[target_headers]
            ordered_df = ordered_df.fillna("")
            ordered_df = ordered_df.astype(str)
            list_of_rows = ordered_df.values.tolist()
            target_ws = get_or_create_worksheet(spreadsheet, target_tab, target_headers)

            import_btn = st.button("Import Data", type="primary", use_container_width=True)
            if import_btn:
                with st.spinner("Bulk uploading data to Google Sheets..."):
                    success = bulk_append_records(target_ws, list_of_rows)

                if success:
                    st.success(f"✅ Successfully imported {len(list_of_rows)} records in bulk!")
                    st.cache_data.clear()

st.markdown("---")
st.subheader("Section C - Tally Export Guide")
st.markdown(
    """
How to export your Tally data for import:
1. Open Tally -> Gateway of Tally
2. Stock Summary -> Alt+E -> Excel format
3. Sales Register -> Alt+E -> Excel format
4. Purchase Register -> Alt+E -> Excel format
5. Upload the exported files in Section B above
"""
)
