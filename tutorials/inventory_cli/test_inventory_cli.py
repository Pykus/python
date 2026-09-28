from datetime import datetime, timezone
import unittest

from inventory_cli import command_audit, command_show, command_summary


class InventoryCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            {
                "hostname": "host-a",
                "hostname_norm": "host-a",
                "serial": "EXAMPLE-001",
                "observed_at": "2026-09-28T08:00:00Z",
                "observed_dt": datetime(2026, 9, 28, 8, tzinfo=timezone.utc),
            },
            {
                "hostname": "host-b",
                "hostname_norm": "host-b",
                "serial": "",
                "observed_at": "2026-07-01T08:00:00Z",
                "observed_dt": datetime(2026, 7, 1, 8, tzinfo=timezone.utc),
            },
        ]

    def test_summary_reports_missing_serial(self) -> None:
        result = command_summary(self.records)
        self.assertEqual(result["devices"], 2)
        self.assertEqual(result["missing_serial"], 1)

    def test_show_is_case_insensitive(self) -> None:
        result = command_show(self.records, "HOST-A")
        self.assertIsNotNone(result)
        self.assertEqual(result["serial"], "EXAMPLE-001")

    def test_audit_reports_stale_and_missing_serial(self) -> None:
        findings = command_audit(
            self.records,
            now=datetime(2026, 9, 28, 12, tzinfo=timezone.utc),
            stale_days=30,
        )
        self.assertEqual(findings[0]["hostname"], "host-b")
        self.assertCountEqual(
            findings[0]["reasons"],
            ["missing_serial", "stale_observation"],
        )


if __name__ == "__main__":
    unittest.main()
