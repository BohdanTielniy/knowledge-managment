#!/usr/bin/env python3
"""Unit / GE-подібний набір тестів якості для CI (python3 -m unittest)."""
import json
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE_DIR, "quality"))
from ci_gate import run_12_quality_checks


class TestKnowledgeHubQualityGate(unittest.TestCase):
    def setUp(self):
        self.records = json.load(open(os.path.join(BASE_DIR, "data", "kb_cleaned.json"), encoding="utf-8"))

    def test_all_12_checks_pass_on_cleaned_kb(self):
        res = run_12_quality_checks(self.records)
        self.assertEqual(len(res), 12)
        for r in res:
            self.assertTrue(r["passed"], f"Failed check {r['id']}: {r['violations']} violations")


if __name__ == "__main__":
    unittest.main()
