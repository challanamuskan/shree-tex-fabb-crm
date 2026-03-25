import json
import re
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def col_letter(col_num):
    result = ""
    while col_num:
        col_num, rem = divmod(col_num - 1, 26)
        result = chr(65 + rem) + result
    return result


def find_credentials_file(project_dir):
    candidates = sorted(Path(project_dir).glob("*.json"))
    for candidate in candidates:
        try:
            with candidate.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if payload.get("type") == "service_account":
                return candidate
        except (OSError, json.JSONDecodeError):
            continue
    return None


def get_service_account_email(credentials_path):
    try:
        with Path(credentials_path).open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload.get("client_email", "")
    except (OSError, json.JSONDecodeError):
        return ""


def build_client(credentials_path):
    creds = ServiceAccountCredentials.from_json_keyfile_name(str(credentials_path), SCOPES)
    return gspread.authorize(creds)


def open_spreadsheet(client, sheet_target):
    target = (sheet_target or "").strip()
    if not target:
        raise ValueError("Spreadsheet ID or name is required.")

    if re.fullmatch(r"[a-zA-Z0-9-_]{30,}", target):
        try:
            return client.open_by_key(target)
        except Exception:
            pass

    return client.open(target)


def get_or_create_worksheet(spreadsheet, tab_name, headers):
    try:
        ws = spreadsheet.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=tab_name,
            rows="1000",
            cols=str(max(10, len(headers) + 2)),
        )
        ws.append_row(headers, value_input_option="USER_ENTERED")
        return ws

    values = ws.get_all_values()
    if not values:
        ws.append_row(headers, value_input_option="USER_ENTERED")
    elif values[0][: len(headers)] != headers:
        ws.update(
            f"A1:{col_letter(len(headers))}1",
            [headers],
            value_input_option="USER_ENTERED",
        )

    return ws


def read_records(worksheet, headers):
    values = worksheet.get_all_values()
    if len(values) <= 1:
        return []

    sheet_headers = values[0]
    indexes = [sheet_headers.index(h) if h in sheet_headers else None for h in headers]

    rows = []
    for row_number, row in enumerate(values[1:], start=2):
        record = {}
        for idx, header in zip(indexes, headers):
            record[header] = row[idx].strip() if idx is not None and idx < len(row) else ""
        record["_row"] = row_number
        rows.append(record)

    return rows


def append_record(worksheet, headers, payload):
    row = [payload.get(header, "") for header in headers]
    worksheet.append_row(row, value_input_option="USER_ENTERED")


def update_record(worksheet, row_number, headers, payload):
    row = [payload.get(header, "") for header in headers]
    worksheet.update(
        f"A{row_number}:{col_letter(len(headers))}{row_number}",
        [row],
        value_input_option="USER_ENTERED",
    )


def delete_record(worksheet, row_number):
    worksheet.delete_rows(row_number)
