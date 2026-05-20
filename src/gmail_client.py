"""Gmail API client: OAuth and message fetching."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Callable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

DEFAULT_QUERY = (
    '(from:notify@payments.interac.ca OR from:payments.interac.ca) '
    '(subject:"INTERAC" OR subject:"e-Transfer" OR subject:"e-transfer")'
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_credentials(
    credentials_path: Path | None = None,
    token_path: Path | None = None,
) -> Credentials:
    root = _project_root()
    credentials_path = credentials_path or root / "credentials.json"
    token_path = token_path or root / "token.json"

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"Missing {credentials_path}. Download OAuth desktop credentials "
                    "from Google Cloud Console (see README)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def build_gmail_service(creds: Credentials | None = None):
    if creds is None:
        creds = get_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def build_search_query(
    base_query: str = DEFAULT_QUERY,
    after: str | None = None,
    before: str | None = None,
) -> str:
    parts = [base_query]
    if after:
        parts.append(f"after:{after}")
    if before:
        parts.append(f"before:{before}")
    return " ".join(parts)


def list_message_ids(
    service,
    query: str,
    max_results: int = 500,
    on_progress: Callable[[str], None] | None = None,
) -> list[str]:
    ids: list[str] = []
    page_token: str | None = None

    while len(ids) < max_results:
        batch_size = min(100, max_results - len(ids))
        result = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=batch_size, pageToken=page_token)
            .execute()
        )
        messages = result.get("messages", [])
        ids.extend(m["id"] for m in messages)
        if on_progress:
            on_progress(f"Found {len(ids)} matching emails…")

        page_token = result.get("nextPageToken")
        if not page_token or not messages:
            break

    return ids[:max_results]


def get_message(service, message_id: str) -> dict:
    return service.users().messages().get(userId="me", id=message_id, format="full").execute()


def decode_body_data(data: str) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
    return raw.decode("utf-8", errors="replace")


def extract_body_from_payload(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")
    if body_data:
        return decode_body_data(body_data)

    parts = payload.get("parts", [])
    plain_parts: list[str] = []
    html_parts: list[str] = []

    for part in parts:
        part_type = part.get("mimeType", "")
        if part_type == "multipart/alternative" or part_type.startswith("multipart/"):
            nested = extract_body_from_payload(part)
            if nested:
                if "html" in part_type.lower():
                    html_parts.append(nested)
                else:
                    plain_parts.append(nested)
            continue
        content = extract_body_from_payload(part)
        if not content:
            continue
        if part_type == "text/plain":
            plain_parts.append(content)
        elif part_type == "text/html":
            html_parts.append(content)

    if plain_parts:
        return "\n".join(plain_parts)
    if html_parts:
        return "\n".join(html_parts)
    return ""


def get_header(headers: list[dict], name: str) -> str:
    name_lower = name.lower()
    for h in headers:
        if h.get("name", "").lower() == name_lower:
            return h.get("value", "")
    return ""


def fetch_messages(
    service,
    query: str,
    max_results: int = 500,
    on_progress: Callable[[str], None] | None = None,
) -> list[dict]:
    message_ids = list_message_ids(service, query, max_results, on_progress)
    messages: list[dict] = []

    for i, mid in enumerate(message_ids):
        if on_progress and (i == 0 or (i + 1) % 10 == 0 or i + 1 == len(message_ids)):
            on_progress(f"Fetching email {i + 1} of {len(message_ids)}…")
        msg = get_message(service, mid)
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        body = extract_body_from_payload(payload)

        messages.append(
            {
                "id": msg.get("id", mid),
                "date": get_header(headers, "Date"),
                "subject": get_header(headers, "Subject"),
                "from_email": get_header(headers, "From"),
                "body": body,
            }
        )

    return messages
