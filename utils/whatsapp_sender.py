import time

import pywhatkit as kit


def send_whatsapp_message(phone_number, message, wait_time=30):
    """
    Send WhatsApp message using pywhatkit.
    
    Args:
        phone_number: Phone number in format +91XXXXXXXXXX or 91XXXXXXXXXX
        message: Message text to send
        wait_time: Seconds to wait before sending (default 30)
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        phone_number = str(phone_number).strip()
        if not phone_number.startswith("+"):
            if phone_number.startswith("91"):
                phone_number = "+" + phone_number
            else:
                phone_number = "+91" + phone_number

        kit.sendwhatmsg_instantly(phone_number, message, wait_time=wait_time)
        return True, f"Message sent to {phone_number}"
    except Exception as exc:
        error_msg = str(exc)
        return False, f"Failed to send to {phone_number}: {error_msg}"
