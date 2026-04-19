import base64, io
from collections import Counter

import streamlit as st
if "username" not in st.session_state or not st.session_state.get("username"):
    st.warning("Please login first.")
    st.stop()
from utils.supabase_db import fetch_table
from utils.ui import init_page
from PIL import Image

init_page("Part Images")
st.title("📸 Part Images Catalogue")

parts = fetch_table("parts")


def _cat(p):
    return (p.get("category") or "").strip() or "Uncategorised"


def _has_image(p):
    return bool(str(p.get("image", "") or "").strip())


parts_with_images = [p for p in parts if _has_image(p)]

# Build image counts for every category that exists in the parts table —
# categories with zero images still appear in the filter so users can see
# the full catalogue shape instead of only the ~9 categories with uploads.
image_counts = Counter(_cat(p) for p in parts_with_images)
all_categories = sorted({_cat(p) for p in parts})

st.caption(
    f"{len(parts_with_images)} of {len(parts)} parts have images "
    f"· {len(image_counts)} of {len(all_categories)} categories have at least one image"
)

if not parts_with_images:
    st.info("No part images uploaded yet. Go to Stock Manager → Edit Part to upload images.")
    st.stop()

def _option_label(cat):
    n = image_counts.get(cat, 0)
    suffix = f"{n} image{'s' if n != 1 else ''}" if n else "no images yet"
    return f"{cat} ({suffix})"

options = ["All"] + all_categories
selected_cat = st.selectbox(
    "Filter by Category",
    options=options,
    format_func=lambda c: "All categories" if c == "All" else _option_label(c),
)

if selected_cat != "All":
    visible = [p for p in parts_with_images if _cat(p) == selected_cat]
else:
    visible = parts_with_images

st.markdown(f"**{len(visible)} parts with images**")

if not visible:
    st.info(f"No images uploaded yet for category **{selected_cat}**.")
    st.stop()

cols = st.columns(3)
for i, part in enumerate(visible):
    with cols[i % 3]:
        try:
            img_bytes = base64.b64decode(part["image"])
            img = Image.open(io.BytesIO(img_bytes))
            st.image(img, use_container_width=True)
        except Exception:
            st.warning("Image error")
        st.markdown(f"**{part.get('part_name','Unnamed')}**")
        st.caption(f"Cat: {part.get('category','N/A')} | Qty: {part.get('quantity','0')} | ₹{part.get('unit_sale_price','0')}")
