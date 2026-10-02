# Jaipuria Moodle Reports MCP: c4-containers

> Raw: [baseline evidence](../raw/2026-10-01-baseline.md)
> Fingerprint: git:997f8797d9731df94ca083fb285155d7c21a7eb5
> Monitored: server.py, security.py, supabase_client.py, tools, guardrails.py, annotations.py, oauth_compat.py, config.py, cache.py, requirements.txt, render.yaml, Dockerfile, Procfile
> Status: Current

```mermaid
C4Container
  title Moodle MCP data and generation boundaries
  Container(host, "Faculty MCP host", "Chat or dashboard client", "Tool routing and explanation")
  Container(mcp, "Moodle MCP server", "Python and FastMCP", "Authentication, grants and structured tools")
  ContainerDb(db, "Institutional report database", "Supabase Postgres", "Source data and report outputs")
  System_Ext(google, "Google Workspace", "Configured faculty OAuth")
  Container(agent, "Report service", "moodle-agent upstream", "Generation and cache writes")
  System_Ext(model, "Report-generation provider", "Upstream model call")
  Rel(host, mcp, "Calls campus-scoped tools", "OAuth or bearer and MCP")
  Rel(mcp, google, "Completes configured sign-in")
  Rel(mcp, db, "Reads with shared server credential", "PostgREST")
  Rel(mcp, agent, "Requests report generation", "HTTPS and server credentials")
  Rel(agent, db, "Persists generated report context")
  Rel(agent, model, "Requests report insight")
```

A configured reporting_readonly role can enforce database SELECT-only access. The legacy service_role fallback can bypass RLS; campus filters and read-only tool code are not interchangeable with least-privilege credentials. The upstream report-service implementation and current deployment are outside this repository snapshot ([evidence](../raw/2026-10-01-baseline.md)).
