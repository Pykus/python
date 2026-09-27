import unittest
import pandas as pd
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("coverage", Path(__file__).with_name("03-coverage-report.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CoverageReportTests(unittest.TestCase):
    def test_marks_unassigned_required_slot_missing(self):
        required = pd.DataFrame([
            {"day":"Mon","break":1,"location":"A"},
            {"day":"Mon","break":1,"location":"B"},
        ])
        assignments = pd.DataFrame([{"day":"Mon","break":1,"location":"A","teacher":"T1"}])
        report = module.coverage_report(assignments, required)
        statuses = dict(zip(report["location"], report["status"]))
        self.assertEqual(statuses, {"A":"covered","B":"missing"})

if __name__ == "__main__":
    unittest.main()
