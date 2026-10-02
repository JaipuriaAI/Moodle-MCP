# Observed decision: semantic documentation agent with separate publisher

Status: observed implementation; human review pending.
Supersedes only the compiler-only/no-automatic-model automation clause of
[the accepted documentation convention](../0001-documentation-convention.md).
Preserves its evidence, provenance and draft-review requirements.
Related: [recorded agent design](../0003-main-push-documentation-agent.md).

The later [owner plan](../../raw/2026-10-01-agent-automation-plan.md) requests
semantic source review after main updates. The merged workflow retains the
compiler as immutable input preparation, adds a Codex documentation agent with
read-only GitHub permissions, and checks its handoff in a separate fresh
publisher checkout before a draft PR. This is observed implementation, not
new human acceptance or proof that publishing completed
([source observations](../../raw/agent-updates/ee905a43042c174e0ab8b9fe5fb9290850c50541-sources.md)).

Recorded alternatives were compiler-only reconciliation and resuming the old
cloud chat; the former cannot interpret diagrams and the latter was unavailable
in the recorded environment. Model API authentication is now required, while
application credentials are unnecessary. Failed remote lookups or partial
publication block paid retries; generated documentation inputs do not trigger
another agent run. Human review and activation/publication evidence remain
pending. Revisit if model permissions, allowed output paths, immutable evidence
or retry policy changes ([evidence](../../raw/agent-updates/ee905a43042c174e0ab8b9fe5fb9290850c50541-sources.md)).
