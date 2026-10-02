"""Exercise simulated agent output and the real Git/diagram handoff pipeline."""
import copy
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_job
from sync import LATEST, RAW_PREFIX, STATE
import test_sync


class AgentHandoffTests(test_sync.ReconciliationTests):
    # Reuse the real-Git fixture, not the compiler test cases.
    for _name in dir(test_sync.ReconciliationTests):
        if _name.startswith("test_"):
            locals()[_name] = None

    def setUp(self):
        super().setUp()
        tools = Path(__file__).parent
        for name in ("agent-prompt.md", "check_mermaid.mjs"):
            self.write("scripts/c5-documentation/" + name, (tools / name).read_text())
        self.commit("Agent tooling")
        self.work = self.repo.parent / (self.repo.name + "-handoff")
        self.work.mkdir()
        self.addCleanup(shutil.rmtree, self.work)
        self.modules = Path(os.environ.get("C5_MERMAID_MODULES", "/workspace/setup/mermaid-validation/node_modules"))

    def start_agent(self):
        self.write("src/main.py", "changed source\n")
        self.target = self.commit("Merged source change")
        return agent_job.prepare(self.repo, self.target, "example/mobile",
                                 "https://github.com/example/mobile/actions/runs/42",
                                 self.work / "context.json", self.work / "prompt.md")

    def simulate_agent(self):
        context = self.start_agent()
        page = self.repo / "docs/architecture/wiki/context.md"
        text = page.read_text().split("<!-- c5-drift -->", 1)[0]
        text = text.replace("git:" + self.base, "git:" + self.target).replace("Status: Outdated", "Status: Current")
        text += "\n```mermaid\nflowchart LR\n  source[Source] --> service[Service]\n```\n"
        page.write_text(text)
        latest = self.repo / LATEST
        latest.write_text(latest.read_text().replace("This is source reconciliation performed by a deterministic compiler.",
                                                    "A documentation agent reviewed the source; original coding-agent identity remains unknown."))
        report = {"summary": "Reconciled the source flow and retained unknown original provenance.",
                  "reviewed_views": ["docs/architecture/wiki/context.md", LATEST],
                  "remaining_gaps": ["Live deployment was not checked."]}
        return context, report

    def bundle(self):
        context, report = self.simulate_agent()
        bundle = agent_job.finish(self.repo, context, report, self.modules, self.work / "bundle.json")
        return context, report, bundle

    def fresh_clone(self):
        fresh = self.work / "publisher"
        subprocess.run(["git", "clone", "--quiet", str(self.repo), str(fresh)], check=True)
        return fresh

    def test_agent_updates_diagram_and_c5_then_fresh_publisher_checks_the_same_source(self):
        context, report, bundle = self.bundle()
        self.assertEqual(report, bundle["report"])
        fresh = self.fresh_clone()
        update = agent_job.restore(fresh, bundle, self.target, "example/mobile", context["run_url"], self.modules)
        self.assertTrue(update["changed"])
        self.assertIn("**main**", update["body"])
        self.assertIn("Codex documentation agent", update["body"])
        self.assertEqual((fresh / "src/main.py").read_text(), "changed source\n")
        self.assertEqual((fresh / "docs/architecture/wiki/context.md").read_text(),
                         (self.repo / "docs/architecture/wiki/context.md").read_text())
        self.assertEqual(json.loads((fresh / STATE).read_text())["code_baseline"], self.target)
        self.commit("Merge agent documentation")
        self.assertFalse(self.run_update()["changed"])

    def test_agent_cannot_edit_application_source(self):
        context, report = self.simulate_agent()
        self.write("src/main.py", "unexpected runtime edit\n")
        with self.assertRaisesRegex(ValueError, "documentation scope"):
            agent_job.finish(self.repo, context, report, self.modules, self.work / "bundle.json")
        self.assertFalse((self.work / "bundle.json").exists())

    def test_agent_cannot_rewrite_prepared_source_evidence(self):
        context, report = self.simulate_agent()
        path = RAW_PREFIX + self.target + ".md"
        self.write(path, "Changed compiler evidence\n")
        with self.assertRaisesRegex(ValueError, "compiler evidence"):
            agent_job.finish(self.repo, context, report, self.modules, self.work / "bundle.json")

    def test_agent_must_review_every_affected_view(self):
        context, report = self.simulate_agent()
        report["reviewed_views"] = [LATEST]
        with self.assertRaisesRegex(ValueError, "not reviewed"):
            agent_job.finish(self.repo, context, report, self.modules, self.work / "bundle.json")

    def test_missing_structured_completion_blocks_publication(self):
        context, report = self.simulate_agent()
        with self.assertRaisesRegex(ValueError, "structured agent completion"):
            agent_job.finish(self.repo, context, {}, self.modules, self.work / "bundle.json")

    def test_old_source_fingerprint_cannot_be_called_reviewed(self):
        context, report = self.simulate_agent()
        path = self.repo / "docs/architecture/wiki/context.md"
        path.write_text(path.read_text().replace(self.target, self.base))
        with self.assertRaisesRegex(ValueError, "target source"):
            agent_job.finish(self.repo, context, report, self.modules, self.work / "bundle.json")

    def test_invalid_mermaid_prevents_artifact_creation(self):
        context, report = self.simulate_agent()
        path = self.repo / "docs/architecture/wiki/context.md"
        path.write_text(path.read_text().replace("source[Source] --> service[Service]", "source[Source -->"))
        with self.assertRaisesRegex(ValueError, "Documentation command failed: node"):
            agent_job.finish(self.repo, context, report, self.modules, self.work / "bundle.json")
        self.assertFalse((self.work / "bundle.json").exists())

    def test_unresolved_view_stays_outdated_with_an_explicit_gap(self):
        context, report = self.simulate_agent()
        path = self.repo / "docs/architecture/wiki/context.md"
        path.write_text(path.read_text().replace("Status: Current", "Status: Outdated"))
        report["remaining_gaps"].append("The upstream contract could not be independently verified.")
        bundle = agent_job.finish(self.repo, context, report, self.modules, self.work / "bundle.json")
        self.assertIn("Status: Outdated", bundle["files"]["docs/architecture/wiki/context.md"])

    def test_invalid_diagram_in_a_new_decision_also_blocks_publication(self):
        context, report = self.simulate_agent()
        self.write(agent_job.AGENT_ADR + self.target + "-decision.md",
                   "# Observed decision\n\n```mermaid\nflowchart LR\n  broken[Node -->\n```\n")
        with self.assertRaisesRegex(ValueError, "Documentation command failed: node"):
            agent_job.finish(self.repo, context, report, self.modules, self.work / "bundle.json")
        self.assertFalse((self.work / "bundle.json").exists())

    def test_publisher_rejects_artifact_from_another_source_or_repository(self):
        context, report, bundle = self.bundle()
        fresh = self.fresh_clone()
        for field, wrong in (("target", "0" * 40), ("repository", "example/other"),
                             ("run_url", "https://github.com/example/mobile/actions/runs/43")):
            bad = dict(bundle, **{field: wrong})
            with self.assertRaisesRegex(ValueError, "does not match"):
                agent_job.restore(fresh, bad, self.target, "example/mobile", context["run_url"], self.modules)
        self.assertEqual(agent_job.changed(fresh), [])

    def test_publisher_rejects_source_paths_and_traversal_before_writing(self):
        context, report, bundle = self.bundle()
        fresh = self.fresh_clone()
        for path in ("src/main.py", "../outside.md", "docs/architecture/wiki/../../../../outside.md"):
            bad = copy.deepcopy(bundle)
            bad["files"][path] = "unapproved change\n"
            with self.assertRaisesRegex(ValueError, "documentation scope"):
                agent_job.restore(fresh, bad, self.target, "example/mobile", context["run_url"], self.modules)
            self.assertEqual(agent_job.changed(fresh), [])

    def test_publisher_rejects_rewritten_raw_evidence_and_log_history(self):
        context, report, bundle = self.bundle()
        fresh = self.fresh_clone()
        bad = copy.deepcopy(bundle)
        bad["files"]["docs/architecture/raw/original.md"] = "rewrite\n"
        with self.assertRaisesRegex(ValueError, "documentation scope"):
            agent_job.restore(fresh, bad, self.target, "example/mobile", context["run_url"], self.modules)
        bad = copy.deepcopy(bundle)
        bad["files"]["docs/architecture/log.md"] = "rewritten history\n"
        with self.assertRaisesRegex(ValueError, "append-only"):
            agent_job.restore(fresh, bad, self.target, "example/mobile", context["run_url"], self.modules)
        self.assertEqual(agent_job.changed(fresh), [])

    def test_publisher_refuses_a_changed_documentation_baseline(self):
        context, report, bundle = self.bundle()
        fresh = self.fresh_clone()
        bundle["files"][STATE] = json.dumps({"version": 1, "code_baseline": self.base})
        with self.assertRaisesRegex(ValueError, "baseline does not match"):
            agent_job.restore(fresh, bundle, self.target, "example/mobile", context["run_url"], self.modules)
        self.assertEqual(agent_job.changed(fresh), [])

    def test_existing_pr_prevents_a_second_paid_agent_run(self):
        self.write("src/main.py", "changed source\n")
        target = self.commit("Merged change")
        with patch.object(agent_job, "command", return_value='[{"url":"https://github.com/example/mobile/pull/1"}]'):
            result = agent_job.prepare(self.repo, target, "example/mobile", "",
                                       self.work / "context.json", self.work / "prompt.md", skip_existing=True)
        self.assertFalse(result["changed"])
        self.assertFalse((self.work / "prompt.md").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_failed_existing_pr_lookup_does_not_launch_agent(self):
        with patch.object(agent_job, "command", side_effect=ValueError("GitHub lookup failed")):
            with self.assertRaisesRegex(ValueError, "GitHub lookup failed"):
                agent_job.prepare(self.repo, self.git("rev-parse", "HEAD"), "example/mobile", "",
                                  self.work / "context.json", self.work / "prompt.md", skip_existing=True)
        self.assertFalse((self.work / "prompt.md").exists())

    def test_json_handoff_rejects_duplicate_fields(self):
        path = self.work / "duplicate.json"
        path.write_text('{"target":"first","target":"second"}')
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            agent_job.read_json(path)

    def test_partially_published_branch_stops_before_another_model_run(self):
        target = self.git("rev-parse", "HEAD")
        with patch.object(agent_job, "command", return_value='[]'), patch.object(agent_job.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
            with self.assertRaisesRegex(ValueError, "branch exists without a PR"):
                agent_job.prepare(self.repo, target, "example/mobile", "",
                                  self.work / "context.json", self.work / "prompt.md", skip_existing=True)
        self.assertFalse((self.work / "prompt.md").exists())

    def test_failed_remote_branch_lookup_does_not_count_as_no_branch(self):
        with patch.object(agent_job.subprocess, "run", return_value=subprocess.CompletedProcess([], 128)):
            with self.assertRaisesRegex(ValueError, "branch lookup failed"):
                agent_job.preflight_branch(self.repo, "automation/c5-docs-" + "0" * 12)

    def test_failed_pr_creation_reports_the_published_branch_and_permission_step(self):
        failed = subprocess.CompletedProcess([], 1, stdout='', stderr='do-not-print-a-credential')
        with patch.object(test_sync.publish.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(ValueError, "PR creation permission") as error:
                test_sync.publish.command(["gh", "pr", "create", "--draft"])
        self.assertIn("published branch", str(error.exception))
        self.assertNotIn("do-not-print", str(error.exception))

    def test_other_failed_commands_keep_their_actual_operation(self):
        failed = subprocess.CompletedProcess([], 1, stdout='', stderr='failure')
        with patch.object(test_sync.publish.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(ValueError, "Command failed: git ls-remote"):
                test_sync.publish.command(["git", "ls-remote"])


if __name__ == "__main__":
    unittest.main()
