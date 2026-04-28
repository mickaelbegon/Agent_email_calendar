import importlib.util
import unittest
import sys
import types


if "dotenv" not in sys.modules and importlib.util.find_spec("dotenv") is None:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda: None
    sys.modules["dotenv"] = dotenv_stub

if "pydantic" not in sys.modules and importlib.util.find_spec("pydantic") is None:
    pydantic_stub = types.ModuleType("pydantic")

    class BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

        def __eq__(self, other):
            return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def Field(default=None, default_factory=None, **_kwargs):
        if default_factory is not None:
            return default_factory()
        return default

    pydantic_stub.BaseModel = BaseModel
    pydantic_stub.Field = Field
    sys.modules["pydantic"] = pydantic_stub

from slot_suggester import suggest_slots_from_schedule


class SlotSuggesterTests(unittest.TestCase):
    def test_parses_availability_view_free_blocks(self):
        schedule = {"value": [{"availabilityView": "0011111111111111"}]}

        slots = suggest_slots_from_schedule(
            schedule,
            60,
            "2026-04-27T09:00:00",
            "2026-04-27T17:00:00",
            timezone="America/Montreal",
        )

        self.assertEqual(len(slots), 1)
        self.assertIn("09:00:00", slots[0].start)
        self.assertIn("10:00:00", slots[0].end)

    def test_detects_multiple_available_slots(self):
        schedule = {"value": [{"availabilityView": "0000001111111111"}]}

        slots = suggest_slots_from_schedule(
            schedule,
            30,
            "2026-04-27T09:00:00",
            "2026-04-27T17:00:00",
            timezone="America/Montreal",
            max_suggestions=3,
        )

        self.assertEqual(len(slots), 3)
        self.assertIn("09:00:00", slots[0].start)
        self.assertIn("09:30:00", slots[1].start)
        self.assertIn("10:00:00", slots[2].start)

    def test_rejects_weekends(self):
        schedule = {"value": [{"availabilityView": "0000000000000000"}]}

        slots = suggest_slots_from_schedule(
            schedule,
            30,
            "2026-05-02T09:00:00",
            "2026-05-02T17:00:00",
            timezone="America/Montreal",
        )

        self.assertEqual(slots, [])

    def test_rejects_slots_outside_work_hours(self):
        schedule = {"value": [{"availabilityView": "000000"}]}

        slots = suggest_slots_from_schedule(
            schedule,
            30,
            "2026-04-27T07:00:00",
            "2026-04-27T10:00:00",
            timezone="America/Montreal",
            max_suggestions=10,
        )

        self.assertEqual(len(slots), 2)
        self.assertTrue(all("09:" in slot.start for slot in slots))

    def test_duration_none_uses_default_duration(self):
        schedule = {"value": [{"availabilityView": "0111111111111111"}]}

        slots = suggest_slots_from_schedule(
            schedule,
            None,
            "2026-04-27T09:00:00",
            "2026-04-27T17:00:00",
            timezone="America/Montreal",
        )

        self.assertEqual(len(slots), 1)
        self.assertIn("09:00:00", slots[0].start)
        self.assertIn("09:30:00", slots[0].end)


if __name__ == "__main__":
    unittest.main()
