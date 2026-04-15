#!/usr/bin/env python3
"""
Run this from your project root:
    python3 patch_stock_manager.py

Fixes:
1. supabase variable not defined → use get_supabase()
2. Daily Activity: auto-insert purchase_record when part is added so
   the activity shows up without needing to go to Purchases page
"""

import re

path = "pages/1_Stock_Manager.py"
content = open(path).read()

# ── Fix 1: supabase variable not defined ─────────────────────────────────────
old1 = "upsert_supplier_contact(supabase, _sname, _sphone, _semail)"
new1 = "upsert_supplier_contact(get_supabase(), _sname, _sphone, _semail)"
assert old1 in content, "Fix 1 target not found — may already be patched"
content = content.replace(old1, new1)
print("✅ Fix 1: supabase variable → get_supabase()")

# ── Fix 2: add get_supabase import if not present ────────────────────────────
if "get_supabase" not in content:
    content = content.replace(
        "from utils.supabase_db import (\n    insert_record,\n    delete_record,\n    fetch_table,\n    update_record,\n)",
        "from utils.supabase_db import (\n    insert_record,\n    delete_record,\n    fetch_table,\n    update_record,\n    get_supabase,\n)",
    )
    print("✅ Fix 2: added get_supabase import")
else:
    print("ℹ️  Fix 2: get_supabase already imported, skipping")

# ── Fix 3: auto-insert purchase_record when new part is added ─────────────────
# Find the block right after insert_record("parts", ...) and before st.success("Part added.")
# We insert a purchase_records row so Daily Activity shows it

old3 = '                    st.success("Part added.")'
new3 = '''                    # Auto-insert purchase record so Daily Activity reflects this addition
                    if int(quantity) > 0:
                        insert_record("purchase_records", {
                            "date": purchase_date.isoformat(),
                            "part_name": part_name.strip(),
                            "category": form_category,
                            "supplier_name": supplier_name.strip(),
                            "quantity_purchased": str(int(quantity)),
                            "purchase_invoice_number": "STOCK-ADD",
                            "purchase_price_per_unit": f"{float(unit_purchase_price):.2f}",
                            "total_purchase_value": f"{float(unit_purchase_price) * int(quantity):.2f}",
                        })
                    st.success("Part added.")'''

if old3 in content:
    content = content.replace(old3, new3)
    print("✅ Fix 3: auto-insert purchase_record on part add")
else:
    print("⚠️  Fix 3: target not found — check manually")

open(path, "w").write(content)
print("\nDone. Restart streamlit to apply changes.")
