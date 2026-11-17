"""Assignment 7: a metered client outside a run, for Part D's judge (checks/FORMATS.md,
section 15.10).

    from harness.meter import judge_session
    with judge_session("test-1") as session:        # the backend settings.yaml names
        response = session.client.create(system=prompt, messages=[{"role": "user", "content": text}])
        session.trace.model_call(0, response, purpose="judge")
        response.text, session.id                     # what the judge said; the session's ID

A judge session is a run of its own: its trace is runs/judge/<session id>.jsonl (a
run_start line with way "judge", your model_call lines, a run_end line), its calls are
priced from pricing.yaml like every run's, and when it closes its tokens go in the
ledger, so they count against lab_token_ceiling. Write the session's ID on every
verdict line, so a checker can match each verdict to a call that made it. To test
your plumbing for nothing:

    with judge_session("plumbing", backend="harness.scripted:PassEverything") as session: ...

PassEverything passes every output: a coin, which your correction must refuse.
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from harness import LAB, ROOT
from harness.backends import REAL_BACKENDS, make_backend
from harness.client import ModelClient
from harness.clock import now as clock_now
from harness.pricing import PriceSheet
from harness.settings import load_settings
from harness.trace import TraceWriter


class Session:
    def __init__(self, id: str, client: ModelClient, trace: TraceWriter, model: str, backend: str):
        self.id, self.client, self.trace, self.model, self.backend = id, client, trace, model, backend


@contextmanager
def judge_session(name: str, backend: str | None = None, *, root: Path = ROOT, over_budget: bool = False):
    """A metered judge session: a client, a trace, and a ledger line when it closes."""
    from harness.runner import Ledger, is_free
    settings = load_settings(root / "settings.yaml")
    backend_name = backend or settings.provider
    if not backend_name or (backend_name in REAL_BACKENDS and not settings.model):
        raise SystemExit("settings.yaml: choose your provider and model first")
    runs_dir = root / "runs"
    ledger = Ledger(runs_dir / "_ledger.jsonl")
    if not is_free(backend_name) and not over_budget and ledger.spent_tokens() >= settings.lab_token_ceiling:
        raise SystemExit(f"lab token ceiling reached ({settings.lab_token_ceiling:,}); ask the course staff "
                         "before you pass over_budget=True")
    prices = PriceSheet(root / "pricing.yaml")
    made = make_backend(backend_name, settings)
    model = settings.model if backend_name in REAL_BACKENDS else getattr(made, "name", backend_name)
    session_id = f"judge-{name}-{uuid.uuid4().hex[:6]}"
    client = ModelClient(made, prices, session_ceiling=settings.session_token_ceiling, run_id=session_id)
    trace = TraceWriter(runs_dir / "judge" / f"{session_id}.jsonl", session_id, {
        "lab": LAB, "way": "judge", "name": name, "backend": backend_name, "model": model,
        "settings": settings.digest(), "price_sheet": prices.read_date, "started_at": clock_now(),
        "started": time.strftime("%Y-%m-%dT%H:%M:%S")})
    error = None
    try:
        yield Session(session_id, client, trace, model, backend_name)
    except BaseException as exc:
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        totals = client.totals()
        trace.run_end(totals, error)
        ledger.append({"run_id": session_id, "way": "judge", "issue": None, "task": None, "sweep": None,
                       "backend": backend_name, "critique": "off", "notes": "off",
                       "total_tokens": totals["total_tokens"], "cost_usd": totals["cost_usd"],
                       "error": error, "quota": False, "rate_limited": False,
                       "finished": time.strftime("%Y-%m-%dT%H:%M:%S")})
