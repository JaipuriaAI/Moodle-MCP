# Rollout validation

Captured: 2026-10-01

- Documentation automation: 17 tests passed. Git fixtures exercise source/runtime-Markdown drift, correct owners, immutable evidence, catch-up, no loops, draft-only publication and both exact checkout URL forms. Remote publication is mocked.
- Documentation checker: zero problems. Mermaid parser: five diagrams passed. Actionlint 1.7.7 passed with shellcheck/pyflakes disabled.
- Existing standalone verification scripts, using the repository venv and fake Supabase configuration: tests/test_hardening.py passed 59 security/generation checks, tests/test_data_fixes.py passed 8 data checks, tests/test_client_wiring.py passed 4 client-wiring checks. These scripts exercise fakes; they are not live data/OAuth/report-service verification. FASTMCP_HOME was set to /workspace/.fastmcp because the cloud user's default home is read-only.
- Runtime source, existing tests, dependency manifests and SQL are unchanged. The older architecture guide is marked historical and README read-only claims are corrected to reflect the existing delegated create_report action.
- No independent reviewer, current database-role audit, live faculty connection, upstream report generation or deployed link-expiry verification ran in this rollout. Main-push publication remains pending merge and Actions PR permission.
