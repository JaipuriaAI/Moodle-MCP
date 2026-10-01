# Reconciliation history

## 2026-10-01: initial rollout

Code baseline: `997f8797d9731df94ca083fb285155d7c21a7eb5`.

Prepared visual C4 onboarding, captured C5 provenance limits and operating constraints, and installed the main-push workflow. [Source evidence](raw/2026-10-01-baseline.md). Remote activation awaits merge; validation is captured in a separate raw record after execution.

## 2026-10-01 - main-push documentation agent

Main source updates now launch a Codex documentation agent through GitHub
Actions to reconcile C4/Mermaid and C5, followed by independent publishing
checks and a draft PR. Model authentication and a successful live main/manual
run remain pending. See the [validation record](raw/2026-10-01-agent-automation-validation.md)
and [activation guide](automation.md).
