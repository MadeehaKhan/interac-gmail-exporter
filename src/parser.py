"""Parse INTERAC e-Transfer notification emails."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape


@dataclass
class TransferRecord:
    date: str
    direction: str
    amount: str
    currency: str
    name: str
    reference_number: str
    subject: str
    from_email: str
    message_id: str
    parse_ok: bool


def strip_html(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"</tr>", "\n", text, flags=re.I)
    text = re.sub(r"</td>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.strip()


def normalize_text(body: str, subject: str) -> str:
    combined = f"{subject}\n{strip_html(body) if '<' in body else body}"
    return unescape(combined)


def classify_direction(text: str, subject: str) -> str:
    combined = f"{subject} {text}".lower()
    sent_cues = (
        "you sent",
        "your transfer to",
        "transfer sent",
        "has been deposited",
        "funds have been sent",
        "vous avez envoyé",
        "transfert envoyé",
    )
    received_cues = (
        "sent you",
        "you received",
        "money received",
        "deposit complete",
        "funds deposited",
        "vous a envoyé",
        "vous a reçu",
        "transfert reçu",
    )
    for cue in sent_cues:
        if cue in combined:
            return "sent"
    for cue in received_cues:
        if cue in combined:
            return "received"
    if "received" in combined or "reçu" in combined:
        return "received"
    if "sent" in combined or "envoyé" in combined:
        return "sent"
    return "unknown"


def extract_amount(text: str) -> tuple[str, str]:
    patterns = [
        r"(?:amount|montant)\s*[:\s]*\$?\s*([\d,]+\.?\d*)",
        r"\$\s*([\d,]+\.\d{2})",
        r"([\d,]+\.\d{2})\s*(?:CAD|cad|\$)",
        r"(?:CAD)\s*\$?\s*([\d,]+\.?\d*)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            amount = m.group(1).replace(",", "")
            currency = "CAD" if re.search(r"CAD|canadian|\$", text, re.I) else ""
            return amount, currency or "CAD"
    return "", ""


def extract_reference(text: str) -> str:
    patterns = [
        r"(?:reference\s*(?:number|no\.?|#)|ref\.?\s*no\.?|confirmation\s*(?:number|#)?)\s*[:\s]*([A-Z0-9][A-Z0-9\-]{4,})",
        r"(?:reference|ref)\s*[:\s]*([A-Z0-9][A-Z0-9\-]{4,})",
        r"(?:transaction|transfer)\s*(?:id|#)\s*[:\s]*([A-Z0-9][A-Z0-9\-]{4,})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1).strip()
    return ""


def extract_name(text: str, direction: str) -> str:
    patterns = [
        r"(?:from|de)\s*[:\s]+([^\n\r<]+?)(?:\s+has|\s+a\s+|\s+sent|\s+envoyé|$)",
        r"(?:sent\s+by|sender)\s*[:\s]+([^\n\r<]+)",
        r"(?:to|à|recipient|destinataire)\s*[:\s]+([^\n\r<]+?)(?:\s+has|\s+will|\s+|$)",
        r"(?:you\s+received\s+(?:money\s+)?from)\s+([^\n\r<\.]+)",
        r"(?:you\s+sent\s+(?:money\s+)?to)\s+([^\n\r<\.]+)",
        r"([A-Za-z][A-Za-z\s\-\.']{2,40})\s+(?:sent\s+you|vous\s+a)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            name = m.group(1).strip()
            name = re.sub(r"\s+", " ", name)
            if len(name) >= 2 and not name.lower().startswith("interac"):
                return name
    return ""


def parse_message(msg: dict) -> TransferRecord:
    subject = msg.get("subject", "")
    body = msg.get("body", "")
    text = normalize_text(body, subject)
    direction = classify_direction(text, subject)
    amount, currency = extract_amount(text)
    reference = extract_reference(text)
    name = extract_name(text, direction)

    parse_ok = bool(amount and reference and name)

    return TransferRecord(
        date=msg.get("date", ""),
        direction=direction,
        amount=amount,
        currency=currency,
        name=name,
        reference_number=reference,
        subject=subject,
        from_email=msg.get("from_email", ""),
        message_id=msg.get("id", ""),
        parse_ok=parse_ok,
    )
