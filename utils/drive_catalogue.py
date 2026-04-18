"""
utils/drive_catalogue.py
Upload part images to Supabase Storage.
"""

import streamlit as st
from supabase import create_client


def upload_image_bytes_to_supabase_storage(
    part_name: str,
    category: str,
    image_bytes: bytes,
) -> str:
    """Upload image bytes to Supabase Storage 'parts-images' bucket.

    Returns the public URL, or "" on any failure.
    """
    if not image_bytes:
        return ""
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        file_path = f"{(category or 'uncategorized').strip()}/{(part_name or 'part').strip()}.jpg"
        supabase.storage.from_("parts-images").upload(file_path, image_bytes)
        return supabase.storage.from_("parts-images").get_public_url(file_path)
    except Exception as e:
        print(f"[STORAGE] upload failed: {type(e).__name__}: {e}")
        return ""


# Backward compatibility wrapper for existing imports
def upload_image_bytes_to_drive(
    part_name: str,
    category: str,
    image_bytes: bytes,
    folder_id: str = None,
) -> str:
    """Backward compatibility. Delegates to Supabase upload."""
    return upload_image_bytes_to_supabase_storage(part_name, category, image_bytes)
