# Main-push documentation agent

Status: proposed implementation; merge and model authentication pending.

## Problem and authorized outcome

The owner requested that each main update launch an agent which understands
the change and updates the visual architecture documentation. Recording a
change and leaving its architecture views stale does not fulfill that goal.

## Choice and alternatives

Keep the deterministic compiler as immutable evidence preparation and run the
official Codex GitHub Action for semantic reconciliation. A separate fresh
publishing job checks the agent's documentation and opens a draft PR.

The earlier compiler-only workflow was considered and implemented, but it
cannot interpret architecture or redraw a meaningful diagram. No supported
tool for remotely resuming this cloud chat was available in this environment.
The Actions route launches a new Codex agent with the repository convention
and explicit source/task metadata.

## Constraints and consequences

Model API authentication is required in GitHub Actions. It is separate from
application credentials and this chat's login. API billing and spending budgets
belong to the API project. Activation remains unverified until an authenticated
main/manual run succeeds.

Preserve raw history and accepted decisions. Historical coding-agent identity,
human approval and unrecorded intent remain unknown. Local simulated handoff
tests and Mermaid parsing do not prove model behavior or semantic correctness.
Human review is pending on the draft PR. No paid reviewer is invoked.

See the [workflow guide](../automation.md) and
[authorized plan](../raw/2026-10-01-agent-automation-plan.md).
