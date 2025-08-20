from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, time
from dateutil import tz

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_PATH = Path(".gmail_token.json")
CLIENT_SECRET = Path("client_secret.json")

def get_local_tz():
    return tz.gettz()  # system local tz (e.g., America/Chicago)

def today_iso_for_gmail_query() -> str:
    """Gmail's 'after:' prefers YYYY/MM/DD (local date)."""
    zone = get_local_tz()
    today = datetime.now(zone).date()
    return today.strftime("%Y/%m/%d")

def gmail_service():
    # Load or create OAuth credentials
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    else:
        if not CLIENT_SECRET.exists():
            raise FileNotFoundError("client_secret.json not found in repo root.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())

    # Build Gmail API client
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def search_message_ids(q: str, max_results: int = 100) -> List[str]:
    svc = gmail_service()
    res = svc.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
    return [m["id"] for m in res.get("messages", [])]

def get_message_meta(msg_id: str) -> Dict[str, Any]:
    svc = gmail_service()
    return svc.users().messages().get(
        userId="me", id=msg_id, format="metadata",
        metadataHeaders=["From","To","Subject","Date"]
    ).execute()

def header(msg: Dict[str, Any], name: str, default: str = "") -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return default
