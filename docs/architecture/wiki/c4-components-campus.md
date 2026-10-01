# Jaipuria Moodle Reports MCP: c4-components-campus

> Raw: [baseline evidence](../raw/2026-10-01-baseline.md)
> Fingerprint: git:997f8797d9731df94ca083fb285155d7c21a7eb5
> Monitored: server.py, security.py, supabase_client.py, tools, guardrails.py, annotations.py, oauth_compat.py, config.py, cache.py, requirements.txt, render.yaml, Dockerfile, Procfile
> Status: Current

```mermaid
C4Component
  title Moodle principal and campus boundary
  Component(transport, "Transport and OAuth guard", "ASGI and FastMCP", "Rejects unauthenticated requests")
  Component(principal, "Principal resolver", "security.py", "Domain and faculty campus grants")
  Component(service, "MoodleService", "Python", "Intersects campus and pins latest run")
  Component(reads, "Read tool modules", "Python", "Bounded report and analytics queries")
  Component(action, "create_report", "Python HTTP proxy", "Checks campus before upstream generation")
  Component(guards, "Projection and error guards", "Python", "Strips internals and returns bounded results")
  ContainerDb(db, "Supabase", "Postgres", "Shared institutional credential")
  System_Ext(agent, "Report service", "Generates report and URL")
  Rel(transport, principal, "Resolves allowed caller")
  Rel(principal, service, "Binds campus grant")
  Rel(reads, service, "Applies authorized campus and run")
  Rel(reads, guards, "Projects bounded result")
  Rel(service, db, "Reads scoped data")
  Rel(action, service, "Checks requested campus")
  Rel(action, agent, "Generates only after access check")
```

A missing grant and an all-campus grant are different states; operator defaults must be reviewed explicitly. Resolving a run ID without first checking its campus can bypass downstream scope assumptions. The generation action must keep its campus gate and non-read-only annotation, despite sharing read-only query helpers ([evidence](../raw/2026-10-01-baseline.md)).

Read [security.py](../../../security.py), [supabase_client.py](../../../supabase_client.py), [actions.py](../../../tools/actions.py), and [oauth_compat.py](../../../oauth_compat.py).
