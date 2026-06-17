import unittest

from classifier import classify_email_rules
from email_parser import ParsedEmail


class ClassifierTests(unittest.TestCase):
    def test_meeting_research_email_is_planning_task(self):
        email = ParsedEmail(
            email_id="1",
            sender="personne@example.com",
            subject="Rencontre projet de recherche",
            date="2026-06-17",
            body="Peux-tu me proposer une disponibilite pour discuter du projet de recherche?",
            source="test",
        )

        assessment = classify_email_rules(email)

        self.assertEqual(assessment.category, "recherche")
        self.assertEqual(assessment.recommended_action, "planifier")
        self.assertEqual(assessment.estimated_minutes, 30)

    def test_information_only_email_is_archive_task(self):
        email = ParsedEmail(
            email_id="2",
            sender="admin@example.com",
            subject="Pour information",
            date="2026-06-17",
            body="FYI, aucune action requise.",
            source="test",
        )

        assessment = classify_email_rules(email)

        self.assertEqual(assessment.recommended_action, "archiver")
        self.assertEqual(assessment.estimated_minutes, 2)


if __name__ == "__main__":
    unittest.main()

