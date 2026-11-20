# Runtime provenance

Configured provider: `openai-compatible`; model: `gemini-3.5-flash-lite`;
endpoint: Google's Gemini OpenAI-compatible endpoint. No credential is stored
in this document. The driver reads `GEMINI_API_KEY` from the process environment
or an ignored local `.env` without executing shell content.

The model and standard paid text-token rates were rechecked against
[Google's first-party pricing page](https://aistudio.google.com/docs/pricing#gemini-3.5-flash-lite):
USD 0.30 input, USD 2.50 output (including thinking), and USD 0.03 cached input
per million tokens. These match the existing model row in `pricing.yaml`; the
rates were not changed. The original source/date metadata remains preserved.
No web grounding tool is used by this assignment's runs.

The configured ceilings remain 1,500,000 tokens per session and 20,000,000 per
assignment. No over-budget option is used. All model runs use the prescribed
metered client; the judge additionally checks current-session usage between
calls, because its ledger entry is finalized when the session closes.

The initial `make ping` attempt failed before any API call because the configured
credential was absent. A prior `_ping.jsonl` is not treated as current connectivity
proof. A fresh real ping is required before the driver starts a paid stage.

The task subset and label-independent 8/26/26 split were committed in `a96a722`
and pushed before real experiments or the new judge implementation. The remote's
SSH route rejected authentication; the equivalent HTTPS route succeeded through
the existing credential helper. Origin now uses that HTTPS URL. No token was
printed or placed in a Git URL.

A generic uncommitted judge draft already existed at the start of this audit.
Its existence has not been re-dated or hidden. The split freeze precedes this
session's judge extensions and any label-driven development or held-out testing;
there were no human labels or real judge verdicts at the freeze boundary.
