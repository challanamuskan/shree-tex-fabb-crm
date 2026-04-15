import base64
import io
import re

from PIL import Image
import pdfplumber
import pytesseract
import streamlit as st


def image_to_base64(image_file) -> str:
    """Convert uploaded file to base64 string."""
    if hasattr(image_file, "seek"):
        image_file.seek(0)

    with Image.open(image_file) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((400, 400))

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=60)
        return base64.b64encode(buffer.getvalue()).decode()


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


def extract_text_from_file(uploaded_file) -> str:
    """Extract text from image or PDF using OCR."""
    try:
        if uploaded_file.type == "application/pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text

        image = Image.open(uploaded_file)
        processed = _preprocess_image_for_ocr(image)
        try:
            text = pytesseract.image_to_string(processed, lang="eng+hin", config="--psm 6 --oem 3")
        except Exception:
            text = pytesseract.image_to_string(processed, lang="eng", config="--psm 6 --oem 3")
        return text
    except Exception:
        return ""


def parse_bill_data(text: str) -> dict:
    """
    Parse extracted text to find common bill fields.
    Returns dict with found values or empty strings.
    """
    result = {
        "amount": "",
        "date": "",
        "invoice_number": "",
        "party_name": "",
        "part_name": "",
        "quantity": "",
    }

    if not text:
        return result

    amount_patterns = [
        r"(?:Rs\.?|INR|₹)\s*(\d+(?:,\d+)*(?:\.\d{2})?)",
        r"(?:Total|Amount|Grand Total)[:\s]+(?:Rs\.?|INR|₹)?\s*(\d+(?:,\d+)*(?:\.\d{2})?)",
        r"(\d+(?:,\d+)*(?:\.\d{2})?)\s*(?:Rs\.?|INR|₹)",
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["amount"] = match.group(1).replace(",", "")
            break

    date_patterns = [
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})",
        r"(?:Date|Dated)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["date"] = match.group(1)
            break

    inv_patterns = [
        r"(?:Invoice|Bill|Receipt|Inv)[.:\s#No]+([A-Z0-9/-]+)",
        r"(?:No\.|Number)[:\s]+([A-Z0-9/-]+)",
    ]
    for pattern in inv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["invoice_number"] = match.group(1).strip()
            break

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) > 1:
        for line in lines[1:4]:
            lower_line = line.lower()
            if len(line) > 3 and not any(
                word in lower_line for word in ["invoice", "bill", "receipt", "date", "rs", "gst"]
            ):
                result["party_name"] = line
                break

    qty_patterns = [
        r"(?:Qty|Quantity|Nos|Units?)[.:\s]+(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:Nos|Units?|Pcs|Pieces)",
    ]
    for pattern in qty_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["quantity"] = match.group(1)
            break

    return result


def upload_and_scan_widget(label: str, key: str, accept_types=["jpg", "jpeg", "png", "pdf"]) -> tuple:
    """
    Upload widget with OCR scanning.
    Returns (base64_string, extracted_data_dict).
    """
    st.markdown(f"**📎 {label}** *(optional — upload to auto-fill fields)*")

    tab1, tab2 = st.tabs(["📁 Upload from Device", "📷 Take Photo"])

    b64_result = ""
    extracted = {}
    uploaded_file_ref = None

    with tab1:
        uploaded_file = st.file_uploader(
            "Choose file",
            type=accept_types,
            key=f"{key}_file",
        )
        if uploaded_file:
            uploaded_file_ref = uploaded_file
            b64_result = image_to_base64(uploaded_file)
            if uploaded_file.type.startswith("image"):
                st.image(uploaded_file, caption="Preview", width=200)
            else:
                st.success(f"✅ {uploaded_file.name} ready")

    with tab2:
        camera_photo = st.camera_input("Take photo", key=f"{key}_camera")
        if camera_photo:
            uploaded_file_ref = camera_photo
            b64_result = image_to_base64(camera_photo)
            st.image(camera_photo, caption="Captured", width=200)

    if uploaded_file_ref and b64_result:
        with st.spinner("🔍 Scanning document..."):
            uploaded_file_ref.seek(0)
            text = extract_text_from_file(uploaded_file_ref)
            if text.strip():
                extracted = parse_bill_data(text)
                if any(extracted.values()):
                    st.success("✅ Data extracted! Fields auto-filled below — please verify before saving.")
                else:
                    st.info("📋 Document uploaded. Could not extract data automatically — please fill fields manually.")
            else:
                st.info("📋 Document uploaded. Please fill fields manually.")

    return b64_result, extracted
