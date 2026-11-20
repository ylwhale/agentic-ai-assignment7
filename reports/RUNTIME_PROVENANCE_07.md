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

## Completed Part C runtime

The ignored local `.env` became accessible and a fresh real ping succeeded before
the pilots. No key value was printed or staged. All 80 measured runs used
`gemini-3.5-flash-lite`, the same frozen subset, empty memory, and
`REVIEWER=scripted:approve-all`. An execution-driver path-shadowing bug was caught
before any pilot ran, fixed/tested, and pushed as `8d7003d`; pilot traces were
therefore never overwritten by threshold creation.

Actual pilot SDs (A 0.190940654, B 0.125) and mean arm-sweep cost ($0.065178167)
produced threshold `756817f`, committed at 2026-11-20 11:32:46 −06:00 and pushed
before the earliest sweep-four start, 2026-11-20 17:33:19.849 UTC. The threshold
and frozen inputs remain unchanged. All 95 pilot measured trace/call files match
their pre-threshold hashes; append-only setup/ledger files also retain their data.

The final result contains 40 runs per arm, 2,691,051 metered experiment tokens
and $0.643755 priced run cost. This excludes separate connectivity pings. It is
not a claim about an account invoice. The original per-session and lab ceilings
were never raised or bypassed. The one held terminal run is a finished measured
failure under the course's definition; no quota/rate-limited attempts were
substituted or silently dropped. Detailed chronology/hashes are in
`reports/PART_C_PROVENANCE_07.json`.
