# Architecture and agent-change documentation convention

Status: adopted for this repository following the user's rollout request.

## What deserves durable documentation

Record the knowledge needed to make the next safe change: product intent,
non-obvious constraints, rejected alternatives, accepted limits, failure modes,
ownership across repositories, rollout dependencies, and evidence gaps.
Code summaries, directory inventories, and routine change lists do not need
their own durable narrative when an agent can recover them from source.

For a routine edit, update existing relevant records or record that no durable
decision changed. Do not manufacture a decision record for every commit.

## C4 and our C5 extension

- **C4:** system context and deployable containers; selected component views
  only where they explain a consequential boundary or difficult workflow.
  The standard fourth level is code. Deployment is a separate view. Libraries
  and SDKs are components or implementation details, not
  independently deployed containers. These rules override inconsistent examples
  in the installed C4 skill.
- **Decision records:** the problem, decision drivers, alternatives actually
  considered, chosen approach, consequences, and reasons to revisit it.
- **C5:** our project extension for agent-assisted change provenance. It links
  the goal, decisions, recorded agent contributions, human interventions,
  validation and remaining gaps to the merged implementation. C5 is not an
  additional level of the standard C4 model.

An agent/model attribution is useful only when a source explicitly records it.
A commit author, co-author line, or a planned review does not establish tool,
model, prompts used, review completion, or approval. Mark missing facts unknown.
Capture concise decisions and outcomes, not entire chats or private reasoning.

## Files and authority

The repository README is the visual entry point for a new developer: keep a
compact Mermaid system map, the agent-to-documentation workflow, and links to
the detailed views and decisions. Reconcile its map whenever those boundaries
change. Avoid duplicating the full evidence or decision history in the README.

```
docs/architecture/
  index.md          map of current views and records
  CONVENTION.md     this process
  log.md            append-only update history
  raw/              immutable, sanitized evidence and coding-agent records
  wiki/             current C4 views and compiled C5 records
  decisions/        proposed, accepted, observed, rejected or superseded decisions
  templates/        short capture templates
  archive/          superseded views; create when needed
```

An **accepted** decision has explicit human approval evidence. **Observed**
means the implementation and rationale were recovered from existing sources;
it must not invent a decider or imply a new approval. Supersede accepted records
with a new linked record when the decision changes. Preserve raw inputs and
past validation evidence instead of rewriting them to match a newer result.

Every compiled wiki page starts with `Raw`, `Fingerprint`, `Monitored`, and
`Status` headers. Use a full code commit ID and repository-relative monitored
paths, including dependencies and configuration that affect the claims. Link
important claims to their specific sources. Keep numbers and quotations next
to a raw-source link that contains them verbatim.

Label evidence as:

- **Observed in source:** present at the inspected code revision.
- **Recorded rationale:** explicitly stated in a linked decision, review or handoff.
- **Validated locally:** a recorded command and result from this session.
- **Inferred:** a synthesis with its inputs, clearly separated from recorded intent.
- **Unknown/unverified:** missing history, deployment, device or integration proof.

A `Current` status means the monitored source has been reconciled. It does not
establish live service health, deployed feature flags, device behavior or
unchanged unmonitored dependencies.

## Coding-agent workflow

Before a material change, read the relevant views and existing decisions.
During work, capture the problem, decision drivers, considered alternatives,
human directions and unexpected constraints. At handoff, use the coding-agent
template to save a short record under `raw/` and link the task/PR when available.
Record tests as passed, failed, skipped, or unrun, with command, scope and result.
An agent may record its own execution evidence; another agent must not convert
a plan or an unsupported claim into a completed validation.

No secret values, credentials, private user content, access tokens, or full
unsanitized conversation exports belong in these files. Record an agent/model
name only if known, and explain unavailable historical evidence as unknown.

## Cloud reconciliation after a main push

1. Use the existing isolated checkout; no new worktree is needed unless requested.
   Preserve local changes. Fetch `main` using the existing Git authentication and
   identify the exact code revision to document. Do not switch a dirty checkout
   or overwrite it with remote code.
2. Compare the previous reconciled revision in `log.md` with the new revision.
   Review the diff, relevant PR/task discussion, raw agent records and decision
   records. A missing PR/API credential does not prevent source-based work.
3. Find affected views through their `Monitored` paths. Read changed paths and
   necessary callers/configuration. Refresh only affected views and decisions;
   record a no-impact reconciliation when no durable knowledge changed.
4. Compile a C5 record for a meaningful change. Connect the actual merged outcome
   to its recorded context. Preserve uncertainty where the coding agent did not
   capture an explanation. Ask for a missing decision only if it blocks a useful
   update; do not ask for application keys for this workflow.
5. Run the documentation checker, review grounding manually, and append the
   target code revision, changed documents, result and gaps to `log.md`. Keep the
   index and README's visual entry point current. Archive or mark outdated a
   view that cannot be reconciled.
6. Deliver the documentation diff for review. Follow the repository's draft/ready
   choice before creating a PR; do not merge, publish or delete branches as a
   side effect of documentation maintenance.

These steps define semantic reconciliation by a cloud coding agent. The
[automatic push workflow](automation.md) compiles merged-change evidence and
captured handoffs, opens a draft PR, and marks affected views outdated for
semantic review. It does not infer missing reasoning or run a language model.
The interview-backend checkout is currently
selected at `staging`; do not silently apply this pilot's `main` policy to it.

## Validation and limits

Run `python docs/architecture/check_docs.py`. It checks relative file links,
including the README's links,
wiki headers, raw-source number/quote grounding, monitored-source drift,
working-tree drift, immutable tracked raw records, and basic C4 alias references.
It does not prove semantic correctness, render diagrams, validate external URLs,
or replace source review. Documentation work does not require application startup
or secret values. Run focused existing tests only when they substantiate a claim.

## Installed skill sources

The Skills CLI copied the following packages into `.agents/skills` and recorded
their sources, pinned revisions and content hashes in `skills-lock.json`:

- [C4 Architecture](../../.agents/skills/c4-architecture/SKILL.md), from
  [softaworks/agent-toolkit](https://github.com/softaworks/agent-toolkit/tree/3027f20f3181758385a1bb8c022d4041dfb4de84/skills/c4-architecture).
- [Architecture Decision Records](../../.agents/skills/architecture-decision-records/SKILL.md), from
  [wshobson/agents](https://github.com/wshobson/agents/tree/156b7a5e7a8b93642628a339ee4039c925b34c7f/plugins/documentation-generation/skills/architecture-decision-records).
- [Grounded Vault](../../.agents/skills/grounded-vault/SKILL.md), from
  [wshobson/agents](https://github.com/wshobson/agents/tree/156b7a5e7a8b93642628a339ee4039c925b34c7f/plugins/documentation-standards/skills/grounded-vault).

This convention narrows their examples to this repository: current views stay
small, decision history stays durable, and evidence gaps remain visible. No
remote skill-registry access is needed for normal documentation updates.
