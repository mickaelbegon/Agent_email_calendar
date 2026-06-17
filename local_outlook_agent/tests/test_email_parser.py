import tempfile
import unittest
from pathlib import Path

from email_parser import load_email_files, parse_csv, parse_txt


class EmailParserTests(unittest.TestCase):
    def test_parse_txt_with_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "email.txt"
            path.write_text(
                "From: personne@example.com\n"
                "Subject: Rencontre recherche\n"
                "Date: 2026-06-17\n"
                "\n"
                "Bonjour, peut-on planifier une rencontre?\n",
                encoding="utf-8",
            )

            email = parse_txt(path)

        self.assertEqual(email.sender, "personne@example.com")
        self.assertEqual(email.subject, "Rencontre recherche")
        self.assertIn("planifier", email.body)

    def test_parse_csv_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "emails.csv"
            path.write_text(
                "sender,subject,date,body\n"
                "a@example.com,Sujet A,2026-06-17,Message A\n"
                "b@example.com,Sujet B,2026-06-18,Message B\n",
                encoding="utf-8",
            )

            emails = parse_csv(path)

        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].subject, "Sujet A")
        self.assertEqual(emails[1].sender, "b@example.com")

    def test_load_email_files_supports_csv_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            (input_dir / "emails.csv").write_text(
                "sender,subject,date,body\n"
                "a@example.com,Sujet A,2026-06-17,Message A\n"
                "b@example.com,Sujet B,2026-06-18,Message B\n",
                encoding="utf-8",
            )

            emails = load_email_files(input_dir, limit=1)

        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Sujet A")


if __name__ == "__main__":
    unittest.main()

