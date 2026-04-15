"""
utils/drive_catalogue.py
Upload part images to Google Drive under:
  Satyam Tex Fabb Catalogue / {category} / {part_name}.jpg

Requires GOOGLE_SERVICE_ACCOUNT_JSON in .streamlit/secrets.toml.
Silently returns "" if credentials are missing or any step fails.
"""

import base64
import io
import json

import streamlit as st


def _get_drive_service():
    """Build and return an authenticated Google Drive service, or raise on failure."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_json = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise KeyError("GOOGLE_SERVICE_ACCOUNT_JSON not set in secrets")

    info = json.loads(creds_json) if isinstance(creds_json, str) else creds_json
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


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


def upload_part_image_to_drive(part_name: str, category: str, image_b64: str) -> str:
    """
    Upload a base64-encoded part image to Google Drive.

    Folder structure:
        Satyam Tex Fabb Catalogue / {category} / {part_name}.jpg

    Returns the shareable Drive file URL, or "" on any failure.
    """
    if not image_b64:
        return ""

    try:
        from googleapiclient.http import MediaIoBaseUpload

        service = _get_drive_service()

        # Build folder structure
        root_id = _get_or_create_folder(service, "Satyam Tex Fabb Catalogue")
        cat_clean = (category or "Uncategorised").strip()
        cat_id = _get_or_create_folder(service, cat_clean, parent_id=root_id)

        # Prepare image bytes
        img_bytes = base64.b64decode(image_b64)
        media = MediaIoBaseUpload(io.BytesIO(img_bytes), mimetype="image/jpeg", resumable=False)

        file_name = f"{(part_name or 'part').strip()}.jpg"
        file_metadata = {"name": file_name, "parents": [cat_id]}

        uploaded = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        ).execute()
        file_id = uploaded.get("id", "")

        # Make publicly readable
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

        return f"https://drive.google.com/file/d/{file_id}/view"

    except KeyError:
        # Missing credentials — expected on first deploy, skip silently
        return ""
    except Exception:
        return ""
