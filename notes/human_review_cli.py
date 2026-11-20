#!/usr/bin/env python3
"""Interactive, author-entered historical trace review. No decisions are generated.

    python3 notes/human_review_cli.py --status
    python3 notes/human_review_cli.py              # next unreviewed run
    python3 notes/human_review_cli.py --run agent-issue-4618-s01-1cd87d

The tool prints the source evidence and asks the human for each review finding.
It will not enter a review until the human provides their own observations.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
NOTES = ROOT / 'notes'
DOCUMENT = NOTES / 'trace-review.md'
EVIDENCE = NOTES / 'trace-evidence'


def reviewed() -> set[str]:
    return set(re.findall(r'^\*\*Run ID:\*\*\s*`([^`]+)`', DOCUMENT.read_text(), flags=re.M))


def all_ids() -> list[str]:
    # Review the agent runs first, then the other three ways, to retain the
    # chronological style of the 12 existing manually reviewed sections.
    paths = sorted(EVIDENCE.glob('*.md'))
    return [p.stem for p in paths if p.name.startswith('agent-')] + [p.stem for p in paths if not p.name.startswith('agent-')]


def ask(prompt: str, *, choices: set[str] | None = None) -> str:
    while True:
        answer = input(prompt + ' ').strip()
        if not answer:
            print('A non-empty answer is required. Ctrl-C to leave without saving.')
            continue
        if choices and answer.lower() not in choices:
            print('Choose one of:', ', '.join(sorted(choices)))
            continue
        return answer


def perform(run_id: str) -> None:
    # Keep the original command/--run/--status interface, sharing the validated,
    # backed-up save path with the fast workflow.
    try:
        from .review_fast import review_one
        from .review_support import Store, extract
    except ImportError:
        from review_fast import review_one
        from review_support import Store, extract
    store = Store(ROOT)
    review_one(store, extract(ROOT, run_id))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--run', help='run ID to review, otherwise next missing agent run')
    args = parser.parse_args(argv)
    done = reviewed()
    pending = [i for i in all_ids() if i not in done]
    if args.status:
        print(f'{len(done)}/40 reviewed; {len(pending)} of the 60 evidence pages remain unreviewed.')
        print('Next:', ', '.join(pending[:8]))
        return 0
    if not pending:
        print('All available runs already reviewed.')
        return 0
    run_id = args.run or pending[0]
    if not (EVIDENCE / f'{run_id}.md').is_file():
        raise SystemExit(f'Unknown run {run_id}')
    try:
        perform(run_id)
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled without saving.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
