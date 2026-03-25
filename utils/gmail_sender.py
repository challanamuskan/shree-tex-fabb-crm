import base64
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_PATH = BASE_DIR / "token.json"
CREDENTIALS_PATH = BASE_DIR / "gmail_credentials.json"


def get_gmail_service():
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            "gmail_credentials.json not found in project folder."
        )

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH),
                GMAIL_SCOPES,
            )
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def send_email(service, recipient_email, subject, body, sender="me"):
    msg = MIMEText(body, "plain", "utf-8")
    msg["to"] = recipient_email
    msg["from"] = sender
    msg["subject"] = subject

    encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    response = service.users().messages().send(
        userId="me",
        body={"raw": encoded_message},
    ).execute()
    return response.get("id", "")
