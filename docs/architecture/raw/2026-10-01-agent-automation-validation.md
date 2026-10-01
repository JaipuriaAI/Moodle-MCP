# Main-push documentation agent validation

Authorized outcome: main updates launch a Codex agent to reconcile C4/C5 and
Mermaid diagrams. The compiler is source-evidence preparation.

Official action: openai/codex-action@86365089eb2b84e0a8fb0717b304f8bdcb13b20e.
Codex CLI and Responses API proxy: 0.159.3, both confirmed in npm registry metadata.
The official action README requires a model API key.

## Executed local checks

C5_MERMAID_MODULES=/workspace/setup/mermaid-validation/node_modules
python -m unittest discover -s scripts/c5-documentation -p 'test_*.py'

Result: 37 tests passed. Model edits are simulated. Real Git histories,
fresh publisher clones, source preservation, source/evidence checks and
Mermaid parsing run directly. No model API call was made.

Checks cover completed agent handoff; missing/invalid completion; unreviewed
views; wrong source, repository or run; application edits; raw/history rewrites;
invalid diagrams in views and decisions; no loop after documentation merge;
existing PR preservation; partial publication and failed lookups before another
paid model run; and actionable PR creation failure diagnostics.

Documentation checker, Actionlint and patch-whitespace checks passed.
Mermaid parsing covers README and all architecture Markdown, including the
automation guide. These checks do not prove architectural meaning.

## Activation and limitations

The model runs with read-only GitHub permissions. A fresh publishing job
checks only allowed documentation before opening a draft PR. Human review
remains pending. Super-outer additionally permits and verifies only its
existing payload-digest declaration, with no runtime behavior change.

CODEX_DOCS_API_KEY must be entered securely in GitHub Actions. Listing Actions
secrets and reading workflow PR permissions return HTTP 403 for this cloud
integration. No secret value was requested in chat or copied to repository
files. API billing belongs to the API project.

A real authenticated main/manual agent run is unrun. The workflow and draft
PRs prepare that run; model authentication and successful PR creation remain
activation prerequisites. Application tests, devices, live services and
deployment were not rerun for this documentation-tooling amendment.
