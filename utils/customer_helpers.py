"""
utils/customer_helpers.py
Shared helper for deduplicating supplier/customer inserts.
"""

from utils.supabase_db import get_supabase


def upsert_supplier_contact(name: str, phone: str, email: str, notes: str = "Auto-added from Stock Manager") -> bool:
    """
    Insert supplier as customer ONLY if no existing row has the same phone OR name.
    Returns True if inserted, False if already existed.
    """
    if not name.strip():
        return False

    sb = get_supabase()

    # Check by phone first
    if phone.strip():
        existing = sb.table("customers").select("id").eq("phone", phone.strip()).execute().data
        if existing:
            return False

    # Check by name (case-insensitive)
    existing_name = sb.table("customers").select("id").ilike("name", name.strip()).execute().data
    if existing_name:
        return False

    sb.table("customers").insert({
        "name": name.strip(),
        "business_name": name.strip(),
        "phone": phone.strip() if phone.strip() else None,
        "email": email.strip() if email.strip() else None,
        "lead_status": "Won",
        "notes": notes,
    }).execute()
    return True
