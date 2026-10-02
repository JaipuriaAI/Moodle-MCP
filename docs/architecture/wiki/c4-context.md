# Jaipuria Moodle Reports MCP: c4-context

> Raw: [baseline evidence](../raw/2026-10-01-baseline.md)
> Fingerprint: git:997f8797d9731df94ca083fb285155d7c21a7eb5
> Monitored: server.py, security.py, supabase_client.py, tools, guardrails.py, annotations.py, oauth_compat.py, config.py, cache.py, requirements.txt, render.yaml, Dockerfile, Procfile
> Status: Current

```mermaid
C4Context
  title Moodle faculty MCP context
  Person(faculty, "Faculty", "Reviews permitted student data")
  System_Ext(host, "MCP host", "Routes tools and frames answers")
  System(mcp, "Moodle Reports MCP", "Campus-scoped data and report access")
  System_Ext(auth, "Google Workspace", "Faculty OAuth identity")
  System_Ext(db, "Student report project", "Institutional source and report data")
  System_Ext(agent, "moodle-agent", "Ingestion and report generation")
  Rel(faculty, host, "Asks about students and reports")
  Rel(host, mcp, "Calls permitted tools", "MCP over HTTP")
  Rel(mcp, auth, "Resolves configured faculty sign-in")
  Rel(mcp, db, "Reads within campus grants")
  Rel(mcp, agent, "Delegates explicit report generation", "Authenticated HTTPS")
```

This faculty boundary differs from the learner-per-user RLS model in Rehearsal MCP. Report generation is a deliberate side effect in an upstream service, even though the MCP itself does not write report tables ([evidence](../raw/2026-10-01-baseline.md)).
