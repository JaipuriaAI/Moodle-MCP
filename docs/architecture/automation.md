# Automatic documentation monitoring

Every push to `main` starts `.github/workflows/c5-documentation.yml`. This is a GitHub event trigger, with manual dispatch for catch-up. It becomes active after this setup PR is merged into main.

The compiler compares the merged baseline in `automation-state.json` with the exact pushed revision. It captures commit IDs and changed paths, links new sanitized handoffs and decisions, marks source-drifted views Outdated, updates the README status, and opens a draft PR into main mentioning @rajikapatel01 @mansigambhir-1313. Repository owners and source roots are configured in `scripts/c5-documentation/config.json`.

Generated documentation-only pushes still start the workflow but return without creating another PR. Runtime Markdown skills and agent instructions are real inputs. The compiler invokes no model or paid reviewer. A draft is the requested review state; repository-level third-party review settings remain outside this workflow.

## Activation and permissions

GitHub Actions must be enabled. In Settings -> Actions -> General -> Workflow permissions, allow GitHub Actions to create and approve pull requests. The workflow only creates PRs; it does not approve them. It requests contents and pull-request write access only in the publisher job and uses the built-in `GITHUB_TOKEN`. No application or provider secret is required. Organization restrictions can override repository settings; the cloud integration may not be allowed to inspect or change these settings.

## Review and failure recovery

Run `python -m unittest discover -s scripts/c5-documentation -p 'test_*.py'` and `python docs/architecture/check_docs.py` before publishing. Review affected architecture and decisions semantically, then update their fingerprints and record actual checks. The compiler does not rewrite diagrams or accepted decisions.

Runs are serialized with cancellation disabled. Each source revision has a unique automation branch. Existing PRs are preserved, remote lookup failures block publication, and branches are never force-pushed. Pending updates catch up from the last merged baseline. Inspect stale drafts manually before merging when newer source pushes supersede their target.

If a branch push succeeds but PR creation fails, inspect the orphaned branch and create its draft manually. Do not delete or overwrite it blindly. Check failures are visible in Actions. A PR created by `GITHUB_TOKEN` does not trigger other PR workflows automatically; the publisher validates its own output first. Other application, integration, deployment and independent-review checks are not established by this workflow.
