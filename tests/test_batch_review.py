"""Non-network tests for the optional human-reviewed batch importer."""
from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "notes" / "batch_review.py"
spec = importlib.util.spec_from_file_location("batch_review", SRC)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class BatchReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        notes = root / "notes"
        evidence = notes / "trace-evidence"
        evidence.mkdir(parents=True)
        (root / "fixtures").mkdir()
        (root / "fixtures" / "closed_issues.yaml").write_text(
            '- {issue: 4618, resolution: "Fixed in #967: src/export/scheduler.ts passes owner locale."}\n', encoding="utf-8"
        )
        (evidence / "agent-issue-4618-s01-test.md").write_text(
            "# Run: agent-issue-4618-s01-test\n\n"
            "**Issue:** #4618 \u2014 French report emails\n"
            "**Agent way:** agent\n"
            "**Termination:** turn_limit \u2014 4 model calls\n"
            "## Tool calls\n"
            "| Step | Tool | Arguments | Outcome / result excerpt | Error? |\n"
            "|---:|---|---|---|---|\n"
            "| 1 | `issues_read` | {} | issue | False |\n"
            "| 4 | `code_read_file` | {} | code | False |\n"
            "## Recorded end state\n"
            "- Labels: `[]`\n"
            "- Comment count: 0\n"
            "- PR count: 0\n"
            "- Closed: `False`\n"
            "- Merges: `0`\n"
            "- Pushes: `[]`\n"
            "- Elsewhere: `[]`\n", encoding="utf-8"
        )
        (notes / "trace-review.md").write_text(
            "## Review Progress\n\n"
            "- **Runs reviewed so far:** 1\n"
            "- **Runs remaining to meet the minimum:** 39\n"
            "- **Issues examined:** #4610\n\n"
            "## Run 1 \u2014 Issue #4610\n\n**Run ID:** `agent-issue-4610-s01-old`\n\n"
            "## Template \u2014 Additional Run Reviews\n", encoding="utf-8"
        )
        self.saved_globals = {n: getattr(mod, n) for n in ("ROOT", "NOTES", "EVIDENCE", "DOCUMENT", "OUT", "QUEUE", "PREVIEW", "CLOSED")}
        self.addCleanup(self.restore)
        mod.ROOT = root
        mod.NOTES = notes
        mod.EVIDENCE = evidence
        mod.DOCUMENT = notes / "trace-review.md"
        mod.OUT = notes / "batch_review"
        mod.QUEUE = mod.OUT / "queue.csv"
        mod.PREVIEW = mod.OUT / "evidence-summary.md"
        mod.CLOSED = root / "fixtures" / "closed_issues.yaml"

    def restore(self):
        for name, value in self.saved_globals.items():
            setattr(mod, name, value)

    def edit_queue(self, **changes):
        with mod.QUEUE.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        rows[0].update(changes)
        mod.write_queue(rows)

    def test_prepare_does_not_mark_reviewed(self):
        before = mod.DOCUMENT.read_text(encoding="utf-8")
        mod.prepare()
        self.assertEqual(mod.DOCUMENT.read_text(encoding="utf-8"), before)
        row = next(iter(mod.read_queue().values()))
        self.assertEqual(row["comment_count"], "0")
        self.assertEqual(row["last_observed_tool"], "code_read_file")
        self.assertEqual(row["last_observed_step"], "4")
        self.assertNotIn("CHECK_UNAUTHORIZED_WRITES", row["mechanical_flags"])
        self.assertEqual(row["verified"], "")
        self.assertIn("NOT HUMAN REVIEWED", mod.PREVIEW.read_text(encoding="utf-8"))

    def test_prepare_preserves_human_entries(self):
        mod.prepare()
        self.edit_queue(expected_decision="act", observation="A decision I entered after reading all the evidence.")
        mod.prepare()
        row = next(iter(mod.read_queue().values()))
        self.assertEqual(row["expected_decision"], "act")
        self.assertEqual(row["observation"], "A decision I entered after reading all the evidence.")

    def test_apply_only_verified_complete_rows_and_is_idempotent(self):
        mod.prepare()
        self.edit_queue(
            expected_decision="act", actual_decision="Began act workflow",
            last_correct_call="code_read_file step 4", first_incorrect_call="stopped too early",
            observation="The run reached its limit before making the required comment, label, and PR.",
            assessment="failed", source_checked="fixtures/closed_issues.yaml issue 4618",
            verified="yes",
        )
        mod.apply(dry_run=True)
        self.assertEqual(len(mod.completed()), 1)
        mod.apply()
        self.assertEqual(len(mod.completed()), 2)
        self.assertIn("**Runs reviewed so far:** 2", mod.DOCUMENT.read_text(encoding="utf-8"))
        self.assertEqual(len(list((mod.OUT / "backups").glob("*.md"))), 1)
        mod.apply()
        self.assertEqual(len(mod.completed()), 2)

    def test_reject_incomplete_verified_row(self):
        mod.prepare()
        self.edit_queue(verified="yes", expected_decision="act")
        before = mod.DOCUMENT.read_text(encoding="utf-8")
        with self.assertRaises(SystemExit):
            mod.apply()
        self.assertEqual(before, mod.DOCUMENT.read_text(encoding="utf-8"))

    def test_bad_status_rejected(self):
        mod.prepare()
        self.edit_queue(
            expected_decision="act", actual_decision="act",
            last_correct_call="issues_read step 1", first_incorrect_call="none",
            observation="The agent took some actions, but these require a correctness review.",
            assessment="maybe", source_checked="source code", verified="yes",
        )
        with self.assertRaises(SystemExit):
            mod.apply()


if __name__ == "__main__":
    unittest.main()
