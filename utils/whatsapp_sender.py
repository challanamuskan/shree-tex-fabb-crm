import urllib.parse


def generate_whatsapp_link(phone_number, message):
    encoded_msg = urllib.parse.quote(message)
    cleaned_num = str(phone_number).replace("+", "").replace(" ", "")
    if len(cleaned_num) == 10:
        cleaned_num = "91" + cleaned_num
    return f"https://wa.me/{cleaned_num}?text={encoded_msg}"
