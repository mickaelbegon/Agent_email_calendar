from dataclasses import dataclass
import csv
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ParsedEmail:
    email_id: str
    sender: str
    subject: str
    date: str
    body: str
    source: str


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self.parts)


def _html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.text()


def _message_body(message) -> str:
    if message.is_multipart():
        html_fallback = ""
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                return part.get_content().strip()
            if content_type == "text/html" and not html_fallback:
                html_fallback = _html_to_text(part.get_content())
        return html_fallback.strip()

    content_type = message.get_content_type()
    content = message.get_content()
    if content_type == "text/html":
        return _html_to_text(content).strip()
    return str(content).strip()


def parse_eml(path: Path) -> ParsedEmail:
    with path.open("rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)

    return ParsedEmail(
        email_id=path.stem,
        sender=str(message.get("from", "")).strip(),
        subject=str(message.get("subject", path.stem)).strip() or path.stem,
        date=str(message.get("date", "")).strip(),
        body=_message_body(message),
        source=str(path),
    )


def parse_txt(path: Path) -> ParsedEmail:
    text = path.read_text(encoding="utf-8", errors="replace")
    headers: dict[str, str] = {}
    body_lines: list[str] = []
    in_headers = True

    for line in text.splitlines():
        if in_headers and not line.strip():
            in_headers = False
            continue
        if in_headers and ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
        else:
            in_headers = False
            body_lines.append(line)

    return ParsedEmail(
        email_id=path.stem,
        sender=headers.get("from", ""),
        subject=headers.get("subject", path.stem) or path.stem,
        date=headers.get("date", ""),
        body="\n".join(body_lines).strip() or text.strip(),
        source=str(path),
    )


def parse_msg(path: Path) -> ParsedEmail:
    try:
        import extract_msg
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Parsing .msg requires the optional dependency extract-msg. "
            "Run: pip install -r requirements.txt"
        ) from exc

    message = extract_msg.Message(str(path))
    return ParsedEmail(
        email_id=path.stem,
        sender=message.sender or "",
        subject=message.subject or path.stem,
        date=str(message.date or ""),
        body=message.body or "",
        source=str(path),
    )


def parse_email_file(path: Path) -> ParsedEmail:
    suffix = path.suffix.lower()
    if suffix == ".eml":
        return parse_eml(path)
    if suffix == ".txt":
        return parse_txt(path)
    if suffix == ".msg":
        return parse_msg(path)
    raise ValueError(f"Unsupported email file type: {path}")


def parse_csv(path: Path) -> list[ParsedEmail]:
    emails: list[ParsedEmail] = []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            subject = row.get("subject") or row.get("sujet") or f"{path.stem}-{index}"
            sender = row.get("sender") or row.get("from") or row.get("expediteur") or ""
            date = row.get("date") or row.get("received") or row.get("recu") or ""
            body = row.get("body") or row.get("contenu") or row.get("message") or ""
            emails.append(
                ParsedEmail(
                    email_id=f"{path.stem}-{index}",
                    sender=sender.strip(),
                    subject=subject.strip(),
                    date=date.strip(),
                    body=body.strip(),
                    source=f"{path}#{index}",
                )
            )
    return emails


def load_email_files(input_dir: Path, limit: int) -> list[ParsedEmail]:
    if not input_dir.exists():
        return []

    candidates: Iterable[Path] = sorted(
        path for path in input_dir.iterdir() if path.suffix.lower() in {".eml", ".txt", ".msg", ".csv"}
    )
    emails: list[ParsedEmail] = []
    for path in candidates:
        if len(emails) >= limit:
            break
        if path.suffix.lower() == ".csv":
            for parsed in parse_csv(path):
                if len(emails) >= limit:
                    break
                emails.append(parsed)
        else:
            emails.append(parse_email_file(path))
    return emails
