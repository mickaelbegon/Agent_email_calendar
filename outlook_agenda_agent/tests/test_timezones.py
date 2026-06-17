import importlib.util
import sys
import types
import unittest
from types import SimpleNamespace


if "dotenv" not in sys.modules and importlib.util.find_spec("dotenv") is None:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv_stub

from main import _local_time_equivalent


class TimezoneTests(unittest.TestCase):
    def test_converts_france_time_to_local_timezone(self):
        analysis = SimpleNamespace(
            requested_timezone="Europe/Paris",
            requested_date="2026-04-30",
            requested_time="14:00",
            local_time_equivalent=None,
        )

        converted = _local_time_equivalent(analysis, "America/Montreal")

        self.assertIn("2026-04-30 08:00", converted)

    def test_converts_reunion_time_to_local_timezone(self):
        analysis = SimpleNamespace(
            requested_timezone="Indian/Reunion",
            requested_date="2026-04-30",
            requested_time="14:00",
            local_time_equivalent=None,
        )

        converted = _local_time_equivalent(analysis, "America/Montreal")

        self.assertIn("2026-04-30 06:00", converted)


if __name__ == "__main__":
    unittest.main()

