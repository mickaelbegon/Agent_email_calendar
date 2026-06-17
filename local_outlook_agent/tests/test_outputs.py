import tempfile
import unittest
from pathlib import Path

from classifier import EmailAssessment
from draft_generator import generate_draft
from email_parser import ParsedEmail
from ics_writer import write_ics


class OutputTests(unittest.TestCase):
    def test_draft_is_local_text_and_not_send_instruction(self):
        email = ParsedEmail(
            email_id="1",
            sender="personne@example.com",
            subject="Question",
            date="2026-06-17",
            body="Bonjour",
            source="test",
        )
        assessment = EmailAssessment(
            category="autre",
            urgency="normale",
            importance="normale",
            estimated_minutes=15,
            recommended_action="repondre",
            rationale="test",
        )

        draft = generate_draft(email, assessment)

        self.assertIn("Brouillon genere localement", draft)
        self.assertIn("Aucun courriel n'a ete envoye", draft)
        self.assertNotIn("sendMail", draft)

    def test_ics_writer_creates_local_calendar_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "block.ics"
            write_ics(
                path,
                title="Traiter courriel",
                description="Bloc local",
                start_iso="2026-06-17T09:00:00-04:00",
                end_iso="2026-06-17T09:30:00-04:00",
            )
            content = path.read_text(encoding="utf-8")

        self.assertIn("BEGIN:VCALENDAR", content)
        self.assertIn("BEGIN:VEVENT", content)
        self.assertIn("SUMMARY:Traiter courriel", content)


if __name__ == "__main__":
    unittest.main()

