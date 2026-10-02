# GitHub checkout compatibility and final automation validation

Captured: 2026-10-01

The pinned Actions checkout implementation constructs HTTPS repository URLs without a .git suffix. Source: [checkout url-helper.ts](https://github.com/actions/checkout/blob/11d5960a326750d5838078e36cf38b85af677262/src/url-helper.ts). The publisher originally accepted only the .git form; that would block an actual main publisher even though PR validation passed. No successful main publisher run is claimed.

The origin check now accepts exactly the two HTTPS URL forms for the same expected owner/repository. It continues rejecting another repository or host before GitHub lookup, push or PR creation. Direct tests use a real temporary Git checkout to publish a draft with the Actions URL form and assert rejection of another origin.

Final automation tests passed: 17. Documentation checker: zero problems. These results establish local behavior; publication uses mocked network calls in tests. Workflow-permission reads returned Resource not accessible by integration (HTTP 403); the Actions PR-creation setting remains unverified.

Every main push starts monitoring. Generated documentation is a no-op input to prevent another automatic PR. Merge the setup PR and ensure Actions can create PRs before expecting monitoring to publish drafts.
