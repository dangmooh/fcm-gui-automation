# Fail-Safe V2 Experiment

This folder is an isolated workspace for redesigning fail-safe behavior without
changing the current runtime path.

Rules for this experiment:

- Do not import this package from `main.py` until the design is ready.
- Keep new runner, policy, and evidence ideas here first.
- Use separate scenario files for validation.
- Move code into `core/` only after the behavior is confirmed.

Current baseline:

- Existing implementation already has `ScenarioRunner`, `StepRunner`,
  `FailSafeManager`, `EvidenceCollector`, and `StateAnalyzer`.
- The next redesign can replace or refine those concepts here without breaking
  the current automation flow.
