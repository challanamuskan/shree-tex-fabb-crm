#!/usr/bin/env python3
"""
Run from project root: python3 ocr_fix.py
Replaces the extract_text_from_file function in utils/file_handler.py
with a version that preprocesses images before OCR.
"""

path = "utils/file_handler.py"
content = open(path).read()

old_func = '''def extract_text_from_file(uploaded_file) -> str:
    """Extract text from image or PDF using OCR."""
    try:
        if uploaded_file.type == "application/pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        image = Image.open(uploaded_file)
        text = pytesseract.image_to_string(image)
        return text
    except Exception:
        return ""'''

new_func = '''def _preprocess_image_for_ocr(image):
    """Boost contrast and binarise image so tesseract reads it more accurately."""
    try:
        from PIL import ImageFilter, ImageEnhance, ImageOps
        # Convert to greyscale
        img = image.convert("L")
        # Resize if too small (tesseract needs ~300dpi equivalent)
        w, h = img.size
        if w < 1000:
            scale = 1000 / w
            img = img.resize((int(w * scale), int(h * scale)))
        # Sharpen then boost contrast
        img = img.filter(ImageFilter.SHARPEN)
        img = ImageEnhance.Contrast(img).enhance(2.5)
        # Binarise (black text / white background)
        img = img.point(lambda x: 0 if x < 140 else 255)
        return img
    except Exception:
        return image


def extract_text_from_file(uploaded_file) -> str:
    """Extract text from image or PDF using OCR with preprocessing."""
    try:
        if uploaded_file.type == "application/pdf":
            with pdfplumber.open(uploaded_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text.strip()

        image = Image.open(uploaded_file)
        processed = _preprocess_image_for_ocr(image)

        # Try Hindi+English first, fall back to English only
        try:
            text = pytesseract.image_to_string(
                processed,
                lang="eng+hin",
                config="--psm 6 --oem 3",
            )
        except pytesseract.TesseractError:
            text = pytesseract.image_to_string(
                processed,
                lang="eng",
                config="--psm 6 --oem 3",
            )
        return text.strip()
    except Exception:
        return ""'''

if old_func in content:
    content = content.replace(old_func, new_func)
    open(path, "w").write(content)
    print("✅ OCR function replaced with preprocessed version.")
else:
    print("⚠️  Exact function text not matched.")
    print("Looking for partial match...")
    if "pytesseract.image_to_string(image)" in content:
        # Minimal targeted fix — just replace the one line
        content = content.replace(
            "        text = pytesseract.image_to_string(image)",
            """        processed = _preprocess_image_for_ocr(image)
        try:
            text = pytesseract.image_to_string(processed, lang="eng+hin", config="--psm 6 --oem 3")
        except Exception:
            text = pytesseract.image_to_string(processed, lang="eng", config="--psm 6 --oem 3")"""
        )
        # Add helper before the function
        if "_preprocess_image_for_ocr" not in content:
            insert_before = "def extract_text_from_file"
            helper = '''def _preprocess_image_for_ocr(image):
    try:
        from PIL import ImageFilter, ImageEnhance
        img = image.convert("L")
        w, h = img.size
        if w < 1000:
            img = img.resize((int(w * 1000/w), int(h * 1000/w)))
        img = img.filter(ImageFilter.SHARPEN)
        img = ImageEnhance.Contrast(img).enhance(2.5)
        img = img.point(lambda x: 0 if x < 140 else 255)
        return img
    except Exception:
        return image


'''
            content = content.replace(insert_before, helper + insert_before)
        open(path, "w").write(content)
        print("✅ Applied targeted OCR fix.")
    else:
        print("❌ Could not find OCR line. Paste utils/file_handler.py lines 85-100.")
