import platform
import subprocess
from datetime import datetime

from email_parser import ParsedEmail


FIELD_SEPARATOR = "\x1e"
RECORD_SEPARATOR = "\x1f"


class OutlookLocalError(RuntimeError):
    pass


def _applescript(limit: int) -> str:
    return f'''
tell application "Microsoft Outlook"
    set fieldDelim to ASCII character 30
    set recordDelim to ASCII character 31
    set outputText to ""
    set inboxMessages to messages of inbox
    set messageCount to count of inboxMessages
    if messageCount is 0 then return ""
    set maxItems to {limit}
    if messageCount < maxItems then set maxItems to messageCount

    repeat with i from 1 to maxItems
        set m to item i of inboxMessages
        set subjectText to ""
        set senderText to ""
        set receivedText to ""
        set bodyText to ""

        try
            set subjectText to subject of m as text
        end try
        try
            set senderText to sender of m as text
        end try
        try
            set receivedText to time received of m as text
        end try
        try
            set bodyText to content of m as text
        end try

        set outputText to outputText & subjectText & fieldDelim & senderText & fieldDelim & receivedText & fieldDelim & bodyText & recordDelim
    end repeat

    return outputText
end tell
'''


def _fetch_recent_emails_macos(limit: int, timeout_seconds: int) -> list[ParsedEmail]:
    script = _applescript(limit)
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise OutlookLocalError("osascript is not available on this macOS system.") from exc
    except subprocess.TimeoutExpired as exc:
        raise OutlookLocalError("Outlook AppleScript request timed out.") from exc

    if result.returncode != 0:
        raise OutlookLocalError(result.stderr.strip() or "Outlook AppleScript failed.")

    raw_output = result.stdout.strip()
    if not raw_output:
        return []

    emails: list[ParsedEmail] = []
    for index, record in enumerate(raw_output.split(RECORD_SEPARATOR), start=1):
        if not record.strip():
            continue
        parts = record.split(FIELD_SEPARATOR)
        while len(parts) < 4:
            parts.append("")
        subject, sender, received, body = parts[:4]
        emails.append(
            ParsedEmail(
                email_id=f"outlook-{index}",
                sender=sender.strip(),
                subject=subject.strip() or "(sans sujet)",
                date=received.strip(),
                body=body.strip(),
                source="outlook-applescript",
            )
        )
    return emails


def _outlook_sender(message) -> str:
    sender_name = str(getattr(message, "SenderName", "") or "").strip()
    sender_email = str(getattr(message, "SenderEmailAddress", "") or "").strip()
    if sender_name and sender_email and sender_name != sender_email:
        return f"{sender_name} <{sender_email}>"
    return sender_email or sender_name


def _outlook_date(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value or "").strip()


def _fetch_recent_emails_windows(limit: int) -> list[ParsedEmail]:
    try:
        import pythoncom
        import win32com.client
    except ModuleNotFoundError as exc:
        raise OutlookLocalError(
            "Outlook local on Windows requires pywin32. Run: pip install -r requirements.txt"
        ) from exc

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        inbox = namespace.GetDefaultFolder(6)
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)

        emails: list[ParsedEmail] = []
        for index, message in enumerate(items, start=1):
            if len(emails) >= limit:
                break

            subject = str(getattr(message, "Subject", "") or "").strip()
            body = str(getattr(message, "Body", "") or "").strip()
            received = _outlook_date(getattr(message, "ReceivedTime", ""))
            emails.append(
                ParsedEmail(
                    email_id=f"outlook-{index}",
                    sender=_outlook_sender(message),
                    subject=subject or "(sans sujet)",
                    date=received,
                    body=body,
                    source="outlook-com",
                )
            )
        return emails
    except Exception as exc:
        raise OutlookLocalError(f"Outlook COM request failed: {exc}") from exc
    finally:
        pythoncom.CoUninitialize()


def fetch_recent_emails(limit: int = 5, timeout_seconds: int = 20) -> list[ParsedEmail]:
    system = platform.system().lower()
    if system == "darwin":
        return _fetch_recent_emails_macos(limit=limit, timeout_seconds=timeout_seconds)
    if system == "windows":
        return _fetch_recent_emails_windows(limit=limit)
    raise OutlookLocalError("Local Outlook access is only supported on macOS and Windows.")
