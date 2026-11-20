"""No-network regression tests for Assignment 7 evaluation code."""
from __future__ import annotations

import json
import math
import unittest
from pathlib import Path
from types import SimpleNamespace

from harness import ROOT
from harness.formats import format_triage_comment
from harness.tasks import load_task, load_state
from eval.grounded import check
from eval.judge import CoinJudge, bootstrap, correct, rates
from eval.metrics import metrics
from eval.stats import (interval, margin, over_tasks, pass_at_k, pass_hat_k, spread,
                        sweeps_needed)


class StatisticsTest(unittest.TestCase):
    def test_pass_at_and_pass_hat_k(self):
        self.assertAlmostEqual(pass_at_k(8, 6, 2), 1 - math.comb(2, 2) / math.comb(8, 2))
        self.assertAlmostEqual(pass_hat_k(8, 6, 2), math.comb(6, 2) / math.comb(8, 2))
        self.assertEqual(pass_hat_k(5, 2, 3), 0.0)
        self.assertEqual(pass_at_k(5, 5, 5), 1.0)

    def test_over_tasks(self):
        values = over_tasks({"a": (5, 3), "b": (5, 5), "c": (5, 0)}, 2)
        self.assertAlmostEqual(values[0], (pass_at_k(5, 3, 2) + 1) / 3)
        self.assertAlmostEqual(values[1], (pass_hat_k(5, 3, 2) + 1) / 3)

    def test_spread_margin_interval_and_power(self):
        self.assertEqual(spread([42.0]), 0.0)
        self.assertAlmostEqual(spread([1, 3, 5]), 2)
        self.assertAlmostEqual(margin(1.5, 10, 1.5, 10), 1.96 * math.sqrt(0.45))
        gain, low, high = interval([3.0, 4.0, 5.0], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(gain, 2.0)
        self.assertLess(low, gain)
        self.assertGreater(high, gain)
        self.assertEqual(sweeps_needed(0.0, 0.0, 0.5), 1)


class MetricsTest(unittest.TestCase):
    def test_slide_27(self):
        path = ROOT / "fixtures" / "traces7" / "s27.jsonl"
        lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        task = SimpleNamespace(reference={"calls": 4,
                         "tools": ["read_issue", "search_repo", "read_file", "post_comment"]})
        actual = metrics(lines, task)
        self.assertEqual(actual["step_count"], 3)
        self.assertAlmostEqual(actual["precision"], 0.8)
        self.assertEqual(actual["recall"], 1.0)
        self.assertEqual(actual["repeats"], 1)
        self.assertEqual(actual["orphans"], 1)
        self.assertFalse(actual["no_tools"])

    def test_no_tool_run(self):
        actual = metrics([{"type": "run_end", "totals": {"cost_usd": 0.01}, "elapsed_s": 5}],
                         SimpleNamespace(reference={"calls": 2, "tools": ["read_issue"]}))
        self.assertEqual(actual["step_count"], -2)
        self.assertIsNone(actual["precision"])
        self.assertTrue(actual["no_tools"])
        self.assertAlmostEqual(actual["cost_usd"], 0.01)


class GroundedTest(unittest.TestCase):
    def setUp(self):
        self.task = load_task(ROOT / "eval" / "golden" / "v1" / "tasks" / "g01.yaml")
        issue = self.task.issue
        content = format_triage_comment("bug", "src/ingest/parser.ts", "This is a draft for review.")
        self.state = {issue: {"comments": [content], "labels": ["bug"],
                              "prs": [{"title": "Draft", "body": "Fix src/ingest/parser.ts"}],
                              "closed": False, "merges": 0, "pushes": [], "elsewhere": []}}

    def test_expected_end_state(self):
        result = check(self.task, self.state)
        self.assertTrue(result["passed"], result["why"])
        self.assertTrue(all(x == "present" for x in result["facts"].values()))

    def test_wrong_label_or_extra_pr_fails(self):
        self.state[self.task.issue]["labels"] = ["feature"]
        self.assertFalse(check(self.task, self.state)["passed"])
        self.state[self.task.issue]["labels"] = ["bug"]
        self.state[self.task.issue]["prs"].append({"title": "another", "body": "src/ingest/parser.ts"})
        self.assertFalse(check(self.task, self.state)["passed"])

    def test_stop_expects_no_actions(self):
        task = load_task(ROOT / "eval" / "golden" / "v1" / "tasks" / "g24.yaml")
        empty = {task.issue: {"comments": [], "labels": [], "prs": [],
                              "closed": False, "merges": 0, "pushes": [], "elsewhere": []}}
        self.assertTrue(check(task, empty)["passed"])
        empty[task.issue]["comments"].append("label: question\nfile: none")
        self.assertFalse(check(task, empty)["passed"])


class JudgeMathTest(unittest.TestCase):
    def test_rates(self):
        verdicts = {"a": "pass", "b": "fail", "c": "pass", "d": "fail"}
        labels = {"a": "pass", "b": "pass", "c": "fail", "d": "fail"}
        self.assertEqual(rates(verdicts, labels), (0.5, 0.5))

    def test_coin_refused(self):
        with self.assertRaises(CoinJudge):
            correct(0.5, 0.55, 0.5)
        with self.assertRaises(CoinJudge):
            correct(0.7, 1.0, 0.05)
        self.assertAlmostEqual(correct(0.85, 0.9, 0.8), (0.85 + 0.8 - 1) / 0.7)

    def test_bootstrap_reproducible(self):
        verdicts = {str(x): ("pass" if x % 3 else "fail") for x in range(40)}
        labels = {str(x): ("pass" if x % 2 else "fail") for x in range(40)}
        self.assertEqual(bootstrap(verdicts, labels, 0.6, resamples=2000, seed=7),
                         bootstrap(verdicts, labels, 0.6, resamples=2000, seed=7))


if __name__ == "__main__":
    unittest.main()
