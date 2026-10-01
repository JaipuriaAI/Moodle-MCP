# Main-push documentation agent plan

Authorized by the owner in this cloud conversation on 2026-10-01.

A main push must launch a Codex agent that reads the merged diff, reconciles
C4 diagrams and non-obvious constraints, and updates C5 provenance before a
validated draft documentation PR is opened. The existing compiler remains a
source-evidence preparation step, rather than the final documentation worker.

Use the official pinned Codex GitHub Action, a bounded runner timeout, and a
GitHub Actions model API secret. Do not reuse or export this chat's login.
No application secrets or live-service dependencies are required.

Keep the agent job's GitHub permissions read-only. A separate fresh-checkout
publisher imports only allowed documentation files, verifies provenance and
Mermaid syntax, and opens a draft PR with the existing repository owners.
Preserve raw history, application code and current accepted decisions. Preserve
Super-outer's existing payload digest gate with its narrow metadata exception.

Verify real Git-history preparation, simulated agent edits, cross-job import,
invalid output rejection and no recursive agent run after documentation merge.
Validate every workflow and update the six existing draft PRs. Do not merge,
mark ready, invoke paid Greptile review, release or delete branches.

Model execution remains unverified until the owner provides an API secret in
GitHub Actions and a successful main/manual run is observed. The current tools
cannot inspect or administer that secret or start/resume this cloud chat from
a GitHub webhook. This workflow launches a new Codex agent on GitHub's runner.

