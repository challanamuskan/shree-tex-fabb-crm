import io
from datetime import date

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

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
from utils.sheets_db import append_record, get_or_create_worksheet, read_records
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
    return out.to_csv(index=False).encode("utf-8")


def make_pdf_summary(title, lines):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, title)
    y -= 30
    c.setFont("Helvetica", 10)
    for line in lines:
        c.drawString(40, y, str(line)[:120])
        y -= 16
        if y < 50:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 50
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


spreadsheet = get_spreadsheet_connection()
if not spreadsheet:
    st.stop()

parts_ws = get_or_create_worksheet(spreadsheet, PARTS_TAB, PARTS_HEADERS)
categories_ws = get_or_create_worksheet(spreadsheet, CATEGORIES_TAB, CATEGORIES_HEADERS)
price_history_ws = get_or_create_worksheet(spreadsheet, PRICE_HISTORY_TAB, PRICE_HISTORY_HEADERS)
contacts_ws = get_or_create_worksheet(spreadsheet, CONTACTS_TAB, CONTACTS_HEADERS)
payments_ws = get_or_create_worksheet(spreadsheet, PAYMENTS_TAB, PAYMENTS_HEADERS)
purchase_ws = get_or_create_worksheet(spreadsheet, PURCHASE_RECORDS_TAB, PURCHASE_RECORDS_HEADERS)
sales_ws = get_or_create_worksheet(spreadsheet, SALES_RECORDS_TAB, SALES_RECORDS_HEADERS)
returns_ws = get_or_create_worksheet(spreadsheet, RETURNS_TAB, RETURNS_HEADERS)

parts = read_records(parts_ws, PARTS_HEADERS)
categories = read_records(categories_ws, CATEGORIES_HEADERS)
price_history = read_records(price_history_ws, PRICE_HISTORY_HEADERS)
contacts = read_records(contacts_ws, CONTACTS_HEADERS)
payments = read_records(payments_ws, PAYMENTS_HEADERS)
purchases = read_records(purchase_ws, PURCHASE_RECORDS_HEADERS)
sales = read_records(sales_ws, SALES_RECORDS_HEADERS)
returns = read_records(returns_ws, RETURNS_HEADERS)

st.subheader("Section A - Export Data")
export_type = st.selectbox(
    "Choose export option",
    ["Export Stock Data", "Export Transaction Data", "Export Full Backup"],
)
export_format = st.selectbox("Format", ["Excel", "CSV", "PDF summary"])

if export_type == "Export Stock Data":
    stock_sheets = {
        PARTS_TAB: records_to_df(parts),
        PRICE_HISTORY_TAB: records_to_df(price_history),
        CATEGORIES_TAB: records_to_df(categories),
    }
    if export_format == "Excel":
        data = make_excel(stock_sheets)
        st.download_button("Download Stock Excel", data=data, file_name=f"stock_data_{date.today().isoformat()}.xlsx")
    elif export_format == "CSV":
        data = make_csv_combined(stock_sheets)
        st.download_button("Download Stock CSV", data=data, file_name=f"stock_data_{date.today().isoformat()}.csv")
    else:
        total_qty = sum(int(float(str(r.get("Quantity", "0") or 0))) for r in parts)
        lines = [
            f"Stock rows: {len(parts)}",
            f"Total quantity across suppliers: {total_qty}",
            f"Categories: {len(categories)}",
            f"Price history records: {len(price_history)}",
        ]
        data = make_pdf_summary("Stock Summary Report", lines)
        st.download_button("Download Stock PDF", data=data, file_name=f"stock_summary_{date.today().isoformat()}.pdf")

elif export_type == "Export Transaction Data":
    c1, c2 = st.columns(2)
    with c1:
        start_date = st.date_input("Start Date", value=date.today(), key="txn_start")
    with c2:
        end_date = st.date_input("End Date", value=date.today(), key="txn_end")

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
        f"Total sales value: ₹{total_sales_value:,.2f} | Total purchase value: ₹{total_purchase_value:,.2f} | Net movement: ₹{net_movement:,.2f}"
    )

    tx_sheets = {
        SALES_RECORDS_TAB: sales_df,
        PURCHASE_RECORDS_TAB: purchases_df,
        RETURNS_TAB: returns_df,
    }

    if export_format == "Excel":
        data = make_excel(tx_sheets)
        st.download_button("Download Transaction Excel", data=data, file_name=f"transactions_{date.today().isoformat()}.xlsx")
    elif export_format == "CSV":
        data = make_csv_combined(tx_sheets)
        st.download_button("Download Transaction CSV", data=data, file_name=f"transactions_{date.today().isoformat()}.csv")
    else:
        lines = [
            f"Date range: {start_date} to {end_date}",
            f"Sales rows: {len(sales_df)}",
            f"Purchase rows: {len(purchases_df)}",
            f"Return rows: {len(returns_df)}",
            f"Total sales value: ₹{total_sales_value:,.2f}",
            f"Total purchase value: ₹{total_purchase_value:,.2f}",
            f"Net movement: ₹{net_movement:,.2f}",
        ]
        data = make_pdf_summary("Transaction Summary Report", lines)
        st.download_button("Download Transaction PDF", data=data, file_name=f"transactions_{date.today().isoformat()}.pdf")

else:
    all_sheets = {}
    for ws in spreadsheet.worksheets():
        values = ws.get_all_values()
        if not values:
            all_sheets[ws.title] = pd.DataFrame()
            continue
        headers = values[0]
        rows = values[1:]
        all_sheets[ws.title] = pd.DataFrame(rows, columns=headers)

    data = make_excel(all_sheets)
    st.download_button(
        "Download Full Backup",
        data=data,
        file_name=f"Satyam_Tex_Fabb_Backup_{date.today().isoformat()}.xlsx",
    )

st.markdown("---")
st.subheader("Section B - Import Data")
if not is_admin():
    st.info("Import is available for admin users only.")
else:
    upload = st.file_uploader("Upload Excel or CSV", type=["xlsx", "csv"], key="import_file")

    target_sheet_options = {
        "Parts": (parts_ws, PARTS_HEADERS),
        "Customers": (contacts_ws, CONTACTS_HEADERS),
        "Payments": (payments_ws, PAYMENTS_HEADERS),
        "Purchase_Records": (purchase_ws, PURCHASE_RECORDS_HEADERS),
        "Sales_Records": (sales_ws, SALES_RECORDS_HEADERS),
    }
    target_name = st.selectbox("Import into", options=list(target_sheet_options.keys()))

    if upload is not None:
        if upload.name.lower().endswith(".csv"):
            input_df = pd.read_csv(upload)
        else:
            input_df = pd.read_excel(upload)

        st.markdown("Preview (first 5 rows)")
        st.dataframe(input_df.head(5), use_container_width=True, hide_index=True)

        target_ws, target_headers = target_sheet_options[target_name]
        source_cols = ["-- Skip --"] + list(input_df.columns)

        st.markdown("Column Mapping")
        mapping = {}
        for header in target_headers:
            default_idx = source_cols.index(header) if header in source_cols else 0
            mapping[header] = st.selectbox(
                f"{header} <-",
                options=source_cols,
                index=default_idx,
                key=f"map_{target_name}_{header}",
            )

        if st.button("Import Data"):
            imported = 0
            for _, row in input_df.iterrows():
                payload = {}
                for header in target_headers:
                    src = mapping[header]
                    payload[header] = "" if src == "-- Skip --" else str(row.get(src, ""))
                append_record(target_ws, target_headers, payload)
                imported += 1
            st.success(f"Import complete: {imported} rows imported successfully.")

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
