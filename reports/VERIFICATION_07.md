# Engineering checkpoint verification

- `make test`: 162 tests run, 160 passed, 2 expected skips, no failures/errors.
- Original `tests.test_eval`: all 11 tests pass unchanged.
- New workflow tests cover exact statistics, complete/duplicate matrices,
  the 1/N zero-variance fallback, threshold timing including unfinished fourth
  sweeps, real/scripted separation, isolated tracker roots, human confirmation,
  duplicate labels, held-out prompt isolation, frozen configuration changes,
  partial-verdict resume, and valid first-failure references.
- `make check-07`: 36/80 automated; no integrity flags. Golden set 16/16,
  mathematics 8/12, trajectories 10/10, split contribution 2/16 in judge row.
  The remaining score requires actual experiment and judge evidence.
- The review document and taxonomy hashes match the beginning of this audit;
  all 40 reviewed observations and nine human categories remain unchanged.
- No protected course harness, fixture, tool, way or checker was edited.
- Staged credential-pattern scan found no credentials or staged `.env` file.
- Engineering/source whitespace check passes. The full staged whitespace check
  reports pre-existing CRLF CSV and generated evidence-excerpt formatting in
  archival data. Those bytes were preserved; no checker or test was relaxed.
  The exact paths/counts are recorded in `STAGING_AUDIT_07.json`.

## Not yet verified or completed

The current execution environment still lacks `GEMINI_API_KEY`; initial real ping
failed before a model call. There are zero real Part C runs, no pilot-derived
threshold, zero human Part D labels, no confirmed human criterion, and no real
frozen-judge validation. No result, threshold spread, human judgment, final
submission tag or Canvas submission was invented. The generic inherited judge
draft predates the freeze in the working tree; this is disclosed in runtime
provenance, not hidden by Git history.

The staff-reviewed 20 points remain separate. Part A's taxonomy, selection and
preliminary saturation are documented. Final experimental interpretation,
first-failure causes/checkpoint replay and criterion/reliability discussion must
be audited against the actual completed evidence before claiming submission
readiness.
