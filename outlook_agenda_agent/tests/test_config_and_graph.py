import importlib
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import patch


if "dotenv" not in sys.modules and importlib.util.find_spec("dotenv") is None:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv_stub


class ConfigTests(unittest.TestCase):
    def test_default_scopes_are_read_only(self):
        import config

        with patch.dict(
            os.environ,
            {
                "TENANT_ID": "tenant",
                "CLIENT_ID": "client",
                "OPENAI_API_KEY": "key",
                "TIMEZONE": "America/Montreal",
                "ENABLE_DRAFT_CREATION": "false",
            },
            clear=True,
        ):
            loaded = config.load_config()

        self.assertIn("Mail.Read", loaded.graph_scopes)
        self.assertIn("Calendars.Read", loaded.graph_scopes)
        self.assertNotIn("Mail.Send", loaded.graph_scopes)
        self.assertNotIn("Calendars.ReadWrite", loaded.graph_scopes)
        self.assertNotIn("Mail.ReadWrite", loaded.graph_scopes)

    def test_draft_creation_adds_read_write_mail_scope_only(self):
        import config

        with patch.dict(
            os.environ,
            {
                "TENANT_ID": "tenant",
                "CLIENT_ID": "client",
                "OPENAI_API_KEY": "key",
                "ENABLE_DRAFT_CREATION": "true",
            },
            clear=True,
        ):
            loaded = config.load_config()

        self.assertIn("Mail.ReadWrite", loaded.graph_scopes)
        self.assertNotIn("Mail.Send", loaded.graph_scopes)
        self.assertNotIn("Calendars.ReadWrite", loaded.graph_scopes)


class GraphDraftTests(unittest.TestCase):
    def test_create_draft_uses_messages_endpoint_without_send(self):
        msal_stub = types.ModuleType("msal")

        class PublicClientApplication:
            def __init__(self, *_args, **_kwargs):
                pass

        msal_stub.PublicClientApplication = PublicClientApplication
        requests_stub = types.ModuleType("requests")

        with patch.dict(sys.modules, {"msal": msal_stub, "requests": requests_stub}):
            sys.modules.pop("graph_client", None)
            graph_client = importlib.import_module("graph_client")
            client = graph_client.GraphClient(
                tenant_id="tenant",
                client_id="client",
                scopes=["Mail.ReadWrite"],
                timezone="America/Montreal",
            )

        captured = {}

        def fake_request(method, path, *, params=None, json=None):
            captured["method"] = method
            captured["path"] = path
            captured["params"] = params
            captured["json"] = json
            return {"id": "draft-id"}

        client._request = fake_request
        result = client.create_draft_reply(
            to_email="person@example.com",
            subject="Re: Rencontre",
            body_text="Brouillon seulement",
        )

        self.assertEqual(result, {"id": "draft-id"})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["path"], "/me/messages")
        self.assertNotIn("sendMail", captured["path"])
        self.assertNotIn("saveToSentItems", captured["json"])
        self.assertEqual(captured["json"]["toRecipients"][0]["emailAddress"]["address"], "person@example.com")


if __name__ == "__main__":
    unittest.main()
