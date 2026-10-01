
## C4/C5 documentation updates

Read `docs/architecture/CONVENTION.md` and `docs/architecture/index.md` before material changes. Keep README's Mermaid map aligned with service boundaries. Capture non-obvious intent, constraints, rejected alternatives, accepted limits, actual agent/human contributions and validation in a sanitized new raw handoff. Unknown historical attribution stays unknown; planned reviews are not executed reviews. Preserve immutable raw inputs and supersede accepted decisions with new linked records.

Run `python docs/architecture/check_docs.py` and the documentation automation tests before publishing documentation. The main-push compiler opens draft PRs, records merged inputs and flags affected views Outdated; reconcile diagrams and decisions semantically before marking them Current. Documentation needs no application secrets or live-service startup.
