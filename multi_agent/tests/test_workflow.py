"""Offline safety regression tests; no LLM or Drive access is required."""
import asyncio
import importlib.util
from pathlib import Path
import unittest


MODULE_FILE = Path(__file__).resolve().parents[1] / "run.py"
SPEC = importlib.util.spec_from_file_location("job_agents_run", MODULE_FILE)
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)


class WorkflowTests(unittest.TestCase):
    def test_hard_pinned_model(self):
        self.assertEqual(run.MODEL, "gpt-6-sol")
        self.assertEqual(run.EFFORT, "high")

    def test_master_preserved(self):
        original = run.load_master()
        self.assertEqual(len(original), 25)
        result = run.merge_jobs(original, [
            {"company": "New Company", "position": "AI Engineer", "source": "careers"},
        ])
        self.assertEqual(len(result), 26)
        self.assertEqual({run.key(x) for x in original} - {run.key(x) for x in result}, set())

    def test_full_original_html_preserved(self):
        html = ("<html><head><title>Old CV</title></head><body>"
                "<p><strong>Position Applied:</strong> AI Engineer</p>"
                "<h2>Introduction</h2><p>Original summary.</p>"
                "<h2>Career Summary</h2><p>Existing jobs unchanged.</p>"
                "</body></html>")
        updated = run.apply_html_changes(html, "AI Agent Engineer", "Builds RAG systems")
        self.assertIn("AI Agent Engineer", updated)
        self.assertIn("Builds RAG systems", updated)
        self.assertIn("Existing jobs unchanged.", updated)
        self.assertNotIn("Original summary.", updated)

    def test_unverified_is_not_verified_new(self):
        job = {"company": "Test", "position": "AI Engineer", "url": "",
               "posted_on": "2026-11-09", "date_evidence": ""}
        status, reason = run.verify_recent(job)
        self.assertEqual(status, "unverified")

    def test_date_from_live_job_schema(self):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch
        today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
        job = {
            "company": "Test", "position": "AI Engineer",
            "url": "https://example.org/jobs/ai-engineer",
            "posted_on": today, "date_evidence": "",
        }
        with patch.object(run.requests, "get") as request:
            request.return_value.url = job["url"]
            request.return_value.text = (
                '<script type="application/ld+json">{"datePosted":"' + today + '"}</script>'
            )
            status, reason = run.verify_recent(job)
        self.assertEqual(status, "verified_new")

    def test_closed_job_is_not_verified(self):
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch
        today = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
        job = {
            "url": "https://example.org/jobs/ai-engineer",
            "posted_on": today, "date_evidence": "",
        }
        with patch.object(run.requests, "get") as request:
            request.return_value.url = job["url"]
            request.return_value.text = (
                '{"datePosted":"' + today + '"} Applications closed'
            )
            status, reason = run.verify_recent(job)
        self.assertEqual(status, "closed")

    def test_report_contains_every_job(self):
        jobs = run.load_master()
        report = run.markdown_report(jobs, "Audit", "DRY_RUN")
        self.assertEqual(report.count("\n| ") - 1, 25)
        for job in jobs:
            self.assertIn(job["company"], report)


if __name__ == "__main__":
    unittest.main()
