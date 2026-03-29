import base64
import io

from PIL import Image
import streamlit as st


def image_to_base64(image_file) -> str:
    """Convert uploaded file to base64 string."""
    bytes_data = image_file.getvalue()
    return base64.b64encode(bytes_data).decode()


def base64_to_image(b64_string: str):
    """Convert base64 string back to displayable image."""
    if not b64_string:
        return None
    try:
        img_bytes = base64.b64decode(b64_string)
        return Image.open(io.BytesIO(img_bytes))
    except Exception:
        return None


def upload_widget(label: str, key: str, accept_types=["jpg", "jpeg", "png", "pdf"]) -> str:
    """
    Show two tabs (Camera and File Upload).
    Return base64 string of uploaded file or empty string.
    """
    st.markdown(f"**📎 {label}** *(optional)*")

    tab1, tab2 = st.tabs(["📁 Upload from Device", "📷 Take Photo"])

    b64_result = ""

    with tab1:
        uploaded_file = st.file_uploader(
            f"Choose file for {label}",
            type=accept_types,
            key=f"{key}_file",
        )
        if uploaded_file:
            b64_result = image_to_base64(uploaded_file)
            if uploaded_file.type.startswith("image"):
                st.image(uploaded_file, caption="Preview", width=200)
            else:
                st.success(f"✅ {uploaded_file.name} uploaded successfully")

    with tab2:
        camera_photo = st.camera_input(
            f"Take photo of {label}",
            key=f"{key}_camera",
        )
        if camera_photo:
            b64_result = image_to_base64(camera_photo)
            st.image(camera_photo, caption="Photo captured", width=200)

    return b64_result


def display_document(b64_string: str, label: str = "View Document"):
    """Display stored document/image."""
    if not b64_string:
        return

    img = base64_to_image(b64_string)
    if img:
        with st.expander(f"🖼️ {label}"):
            st.image(img, width=300)
