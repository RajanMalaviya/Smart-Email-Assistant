import base64
from email.utils import parsedate_to_datetime
from typing import Tuple

def b64url_decode(data_b64url: str) -> bytes:
    # Gmail uses url-safe base64 without padding sometimes
    import base64
    data = data_b64url.encode("ascii")
    rem = len(data) % 4
    if rem:
        data += b"=" * (4 - rem)
    return base64.urlsafe_b64decode(data)

def extract_plain_html_from_gmail_payload(payload: dict) -> Tuple[str, str]:
    """
    Walks payload parts to find 'text/plain' and 'text/html' bodies.
    Returns (plain_text, html_text)
    """
    plain = ""
    html = ""
    def walk(part):
        nonlocal plain, html
        if not part:
            return
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        data = body.get("data")
        if data:
            try:
                text = b64url_decode(data).decode("utf-8", errors="replace")
            except Exception:
                text = ""
            if mime == "text/plain":
                plain += text
            elif mime == "text/html":
                html += text
            else:
                # sometimes top-level body with mimeType "text/plain"
                if not plain and mime.startswith("text/"):
                    plain += text
        # parts
        for p in part.get("parts", []) or []:
            walk(p)
    walk(payload)
    return plain.strip(), html.strip()

def clean_email_text(snippet: str) -> str:
    """Remove unwanted characters from snippet"""
    return snippet.strip().replace("\n", " ")