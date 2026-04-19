import base64, io
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
parts_with_images = [p for p in parts if str(p.get("image","")).strip()]

if not parts_with_images:
    st.info("No part images uploaded yet. Go to Stock Manager → Edit Part to upload images.")
    st.stop()

categories = sorted(set((p.get("category","") or "Uncategorised") for p in parts_with_images))
selected_cat = st.selectbox("Filter by Category", ["All"] + categories)
if selected_cat != "All":
    parts_with_images = [p for p in parts_with_images if (p.get("category","") or "Uncategorised") == selected_cat]

st.markdown(f"**{len(parts_with_images)} parts with images**")
cols = st.columns(3)
for i, part in enumerate(parts_with_images):
    with cols[i % 3]:
        try:
            img_bytes = base64.b64decode(part["image"])
            img = Image.open(io.BytesIO(img_bytes))
            st.image(img, use_container_width=True)
        except:
            st.warning("Image error")
        st.markdown(f"**{part.get('part_name','Unnamed')}**")
        st.caption(f"Cat: {part.get('category','N/A')} | Qty: {part.get('quantity','0')} | ₹{part.get('unit_sale_price','0')}")
