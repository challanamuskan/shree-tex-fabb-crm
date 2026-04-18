"""
utils/drive_catalogue.py
Upload part images to Google Drive.

Supports two upload modes:
  1. Direct to CATALOGUE_FOLDER_ID (default for per-part uploads)
  2. Folder structure: Satyam Tex Fabb Catalogue / {category} / {part_name}.jpg

Credentials read from [gcp_service_account] section in .streamlit/secrets.toml.
Falls back to GOOGLE_SERVICE_ACCOUNT_JSON if gcp_service_account section absent.
Silently returns "" if credentials are missing or any step fails.
"""

import base64
import io
import json

import streamlit as st

# Google Drive folder where part images are stored
CATALOGUE_FOLDER_ID = "1lqqi2hmGoYCf2hCUBdY30kKhWhAXnWL9"


def _get_drive_service(timeout: int = 60):
    """Build and return an authenticated Google Drive service, or raise on failure.

    Note: `timeout` kwarg is accepted for backward compatibility with existing
    callers but is ignored — googleapiclient uses its own default HTTP client.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    # Try structured [gcp_service_account] section first (secrets.toml format)
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
    elif "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
        creds_json = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
        info = json.loads(creds_json) if isinstance(creds_json, str) else dict(creds_json)
    else:
        raise KeyError("No Google service account credentials found in secrets")

    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(service, name: str, parent_id: str = None) -> str:
    """Return folder ID, creating it if it doesn't exist under parent_id."""
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = service.files().list(q=query, fields="files(id)", pageSize=1).execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_part_image_to_drive(
    part_name: str,
    category: str,
    image_b64: str,
    folder_id: str = None,
) -> str:
    """
    Upload a base64-encoded part image to Google Drive.

    If folder_id is provided, uploads directly to that folder.
    Otherwise builds folder structure:
        Satyam Tex Fabb Catalogue / {category} / {part_name}.jpg

    Returns the shareable Drive file URL, or "" on any failure.
    """
    if not image_b64:
        return ""

    import socket
    _TIMEOUT_EXC = (TimeoutError, socket.timeout)

    for _attempt in range(2):  # one try + one retry on timeout
        try:
            from googleapiclient.http import MediaIoBaseUpload

            service = _get_drive_service(timeout=60)

            if folder_id:
                target_folder_id = folder_id
            else:
                root_id = _get_or_create_folder(service, "Satyam Tex Fabb Catalogue")
                cat_clean = (category or "Uncategorised").strip()
                target_folder_id = _get_or_create_folder(service, cat_clean, parent_id=root_id)

            img_bytes = base64.b64decode(image_b64)
            media = MediaIoBaseUpload(io.BytesIO(img_bytes), mimetype="image/jpeg", resumable=False)

            file_name = f"{(part_name or 'part').strip()}.jpg"
            file_metadata = {"name": file_name, "parents": [target_folder_id]}

            uploaded = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
            ).execute()
            file_id = uploaded.get("id", "")

            # Make publicly readable (anyone with link)
            service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()

            return f"https://drive.google.com/file/d/{file_id}/view"

        except _TIMEOUT_EXC as _te:
            if _attempt == 0:
                print(f"[DRIVE] timeout on attempt 1, retrying: {_te}")
                continue
            print(f"[DRIVE] timeout on retry attempt 2, giving up: {_te}")
            return ""
        except KeyError as _ke:
            print(f"[DRIVE] credential key error: {_ke}")
            return ""
        except Exception as _ex:
            print(f"[DRIVE] upload failed: {type(_ex).__name__}: {_ex}")
            return ""

    return ""


def upload_image_bytes_to_drive(
    part_name: str,
    category: str,
    image_bytes: bytes,
    folder_id: str = CATALOGUE_FOLDER_ID,
) -> str:
    """Upload raw image bytes to Drive. Returns shareable URL or '' on failure."""
    if not image_bytes:
        return ""
    b64 = base64.b64encode(image_bytes).decode()
    return upload_part_image_to_drive(part_name, category, b64, folder_id=folder_id)
