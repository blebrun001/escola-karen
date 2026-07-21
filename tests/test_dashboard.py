import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from escola_karen.core import DocumentResult, Offer, RegionResult, load_json
from escola_karen.dashboard import build_report, build_static_site, persist_dashboard_run


def result(name="Tarragona", specialty="GE", error=""):
    documents = [] if error else [
        DocumentResult(
            title="Oferta oficial",
            url="https://example.test/oferta.pdf",
            status="nou",
            sha256="abc",
            offers=[
                Offer(
                    identifier="DC-1",
                    specialty=specialty,
                    institution="Institut Exemple",
                    municipality="Tarragona",
                    vacancies=1.0,
                    deadline="18/07/2026",
                )
            ],
        )
    ]
    return RegionResult(
        name=name,
        page_url="https://example.test/territori",
        documents=documents,
        error=error,
    )


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 7, 16, 15, 5, tzinfo=timezone.utc)

    def test_report_summary_and_changes(self):
        first = build_report([result()], {"GE", "CLA"}, self.now)
        self.assertEqual(first["status"], "success")
        self.assertEqual(first["summary"]["interesting_count"], 1)
        self.assertEqual(len(first["changes"]["added"]), 1)
        self.assertNotIn("detail", first["offers"][0])
        second = build_report([result(specialty="CLA")], {"GE", "CLA"}, self.now, first)
        self.assertEqual(len(second["changes"]["added"]), 1)
        self.assertEqual(len(second["changes"]["removed"]), 1)

    def test_partial_and_error_statuses(self):
        partial = build_report(
            [result(), result(name="Penedès", error="Font inaccessible")],
            {"GE", "CLA"},
            self.now,
        )
        self.assertEqual(partial["status"], "partial")
        failed = build_report([result(error="Font inaccessible")], {"GE", "CLA"}, self.now)
        self.assertEqual(failed["status"], "error")

    def test_removed_document_is_counted_only_for_successful_regions(self):
        first = build_report([result()], {"GE", "CLA"}, self.now)
        empty = RegionResult(
            name="Tarragona",
            page_url="https://example.test/territori",
            documents=[],
        )
        second = build_report([empty], {"GE", "CLA"}, self.now, first)
        self.assertEqual(second["summary"]["documents"]["removed"], 1)
        failed = build_report(
            [result(error="Font inaccessible")], {"GE", "CLA"}, self.now, first
        )
        self.assertEqual(failed["summary"]["documents"]["removed"], 0)

    def test_complete_error_preserves_latest_valid_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            state = root / "state.json"
            first = persist_dashboard_run([result()], {"GE", "CLA"}, self.now, data, state)
            persist_dashboard_run(
                [result(error="Font inaccessible")],
                {"GE", "CLA"},
                self.now + timedelta(days=1),
                data,
                state,
            )
            latest = load_json(data / "latest.json", {})
            status = load_json(data / "status.json", {})
            self.assertEqual(latest["generated_at"], first["generated_at"])
            self.assertEqual(status["status"], "error")

    def test_history_index_is_limited_to_90_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            state = root / "state.json"
            for day in range(95):
                persist_dashboard_run(
                    [result()], {"GE", "CLA"}, self.now + timedelta(days=day), data, state
                )
            index = load_json(data / "history" / "index.json", {})
            self.assertEqual(len(index["entries"]), 90)

    def test_static_page_is_catalan(self):
        project_root = Path(__file__).resolve().parents[1]
        html = (project_root / "dashboard" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<html lang="ca">', html)
        self.assertIn("Darrera actualització", html)
        self.assertNotIn("Dernière mise à jour", html)

    def test_static_page_exposes_daily_radar_and_progressive_exploration(self):
        project_root = Path(__file__).resolve().parents[1]
        html = (project_root / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (project_root / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="priority-offers"', html)
        self.assertIn('id="offers-disclosure"', html)
        self.assertIn('id="show-more"', html)
        self.assertIn("const PAGE_SIZE = 25", script)
        self.assertIn("showPriorityOffer", script)

    def test_static_builder_copies_data(self):
        project_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "data"
            data.mkdir()
            (data / "latest.json").write_text("{}", encoding="utf-8")
            output = root / "site"
            build_static_site(project_root / "dashboard", data, output)
            self.assertTrue((output / "index.html").exists())
            self.assertTrue((output / "data" / "latest.json").exists())
