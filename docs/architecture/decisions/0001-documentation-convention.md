# Decision: preserve architecture and agent-change context

Status: accepted for this rollout.
Decider: the requesting repository owner, through the cloud task conversation.

## Context and choice

Agents can recover ordinary code structure. They cannot recover discarded alternatives, product intent, actual human interventions, missing historical agent identities, or which checks really ran. Keep those facts in concise C5 handoffs and decision records, alongside source-backed C4 diagrams.

Use the mobile pilot convention across the requested repositories. The user authorized sequential PRs and main-push monitoring and asked to avoid unnecessary paid review ([captured request](../raw/2026-10-01-baseline.md)).

## Consequences

The automatic compiler records merged metadata and links new context. It flags architecture drift for semantic review. It cannot invent historical rationale or independently redesign diagrams. Run no language model automatically; use the built-in GitHub Actions token and open drafts. No auto-merge is authorized.
