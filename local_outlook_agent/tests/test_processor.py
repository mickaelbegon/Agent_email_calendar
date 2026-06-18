import tempfile
import unittest
from pathlib import Path

from email_parser import ParsedEmail
from processor import process_emails


class ProcessorTests(unittest.TestCase):
    def test_process_emails_writes_local_outputs_without_sending(self):
        email = ParsedEmail(
            email_id="1",
            sender="personne@example.com",
            subject="Rencontre projet",
            date="2026-06-17",
            body="Peux-tu proposer une disponibilite pour une rencontre?",
            source="test",
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            processed = process_emails(
                [email],
                output_dir=output_dir,
                timezone="America/Montreal",
                max_personal_block_minutes=120,
                llm_mode="rules",
                openai_api_key="",
                create_ics=True,
            )

            self.assertEqual(len(processed), 1)
            self.assertTrue((output_dir / "tasks.csv").exists())
            self.assertTrue(processed[0].draft_path.exists())
            self.assertTrue(processed[0].ics_path.exists())
            self.assertIn("Aucun courriel n'a ete envoye", processed[0].draft_text)


if __name__ == "__main__":
    unittest.main()

