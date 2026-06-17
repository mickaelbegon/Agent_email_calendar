import subprocess

from email_parser import ParsedEmail


FIELD_SEPARATOR = "\x1e"
RECORD_SEPARATOR = "\x1f"


class OutlookAppleScriptError(RuntimeError):
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


def fetch_recent_emails(limit: int = 5, timeout_seconds: int = 20) -> list[ParsedEmail]:
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
        raise OutlookAppleScriptError("osascript is not available on this macOS system.") from exc
    except subprocess.TimeoutExpired as exc:
        raise OutlookAppleScriptError("Outlook AppleScript request timed out.") from exc

    if result.returncode != 0:
        raise OutlookAppleScriptError(result.stderr.strip() or "Outlook AppleScript failed.")

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

