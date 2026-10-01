# Observed decisions: faculty grants and delegated report generation

Status: observed. Historical deciders and original coding-agent/model identities are unknown.

## Campus scoping differs from learner RLS

Faculty data uses an institution-wide database client with a per-request principal. Campus grants must constrain every query, including resolution of the run ID used by downstream joins. The configured OAuth default grants all campuses unless an operator chooses a narrower default or per-faculty override. A valid workspace identity alone does not establish the intended campus permission policy ([evidence](../raw/2026-10-01-baseline.md)).

## Read-only queries do not make generation read-only

create_report checks campus access and delegates generation/cache writes to moodle-agent with server-to-server credentials. It does not email the report. Distinguish reading an existing report from triggering fresh generation and possible model cost; preserve the action's non-read-only annotation. The historical README promise that no tool generates was superseded by the merged action ([source and change record](../raw/2026-10-01-baseline.md)).

## Credential and compatibility boundaries

The database client supports an anon gateway key plus a reporting_readonly JWT bearer. A full service_role credential is a legacy fallback with broader authority, not a SELECT-only role. Keep server credentials out of returned results and verify actual grants before making deployment claims. OAuth compatibility tolerates the recorded cross-client race only when PKCE binds the authorization code; FastMCP is pinned because the override mirrors its internals ([evidence](../raw/2026-10-01-baseline.md)).

## Revisit conditions

Revisit when faculty grant defaults, campus/run joins, DB role grants, provider internals, report-service authorization, caching or share-link expiry changes. Unit fakes and source inspection do not establish live schema, OAuth, downstream report generation or link guarantees.
