"""Exercise a real Git history; no GitHub or application credentials are used."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publish
from sync import BEGIN, CONFIG, END, LATEST, RAW_PREFIX, STATE, prepare


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="c5-history-")
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.write(CONFIG, json.dumps({"version": 1, "source_roots": ["src"], "mentions": ["fixture-owner"], "reviewers": ["fixture-reviewer"]}))
        self.write("src/main.py", "original source\n")
        self.write("README.md", f"# Fixture\n\n{BEGIN}\nInitial status\n{END}\n")
        self.write("docs/architecture/raw/original.md", "Original context\n")
        self.write("docs/architecture/log.md", "# Log\n")
        checker = Path(__file__).resolve().parents[2] / "docs/architecture/check_docs.py"
        shutil.copyfile(checker, self.repo / "docs/architecture/check_docs.py")
        self.base = self.commit("Initial source")
        self.write(STATE, json.dumps({"version": 1, "code_baseline": self.base}))
        self.write("docs/architecture/wiki/context.md",
                   f"# Context\n\n> Raw: [original](../raw/original.md)\n> Fingerprint: git:{self.base}\n> Monitored: src/main.py\n> Status: Current\n\nSource-backed view.\n")
        self.commit("Documentation baseline")

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True, stderr=subprocess.DEVNULL).strip()

    def commit(self, subject):
        self.git("add", ".")
        self.git("commit", "-qm", subject)
        return self.git("rev-parse", "HEAD")

    def run_update(self):
        return prepare(self.repo, self.git("rev-parse", "HEAD"), "example/mobile", "https://github.com/example/mobile/actions/runs/42")

    def test_source_push_preserves_code_and_marks_architecture_honestly(self):
        secret = "do-not-copy-this-configuration-value"
        self.write("src/main.py", secret + "\n")
        target = self.commit("Change source")
        original_raw = (self.repo / "docs/architecture/raw/original.md").read_bytes()
        result = self.run_update()
        self.assertTrue(result["changed"])
        self.assertIn("@fixture-owner", result["body"])
        self.assertIn("**main**", result["body"])
        self.assertIn("> Status: Outdated", (self.repo / "docs/architecture/wiki/context.md").read_text())
        self.assertIn("unknown", (self.repo / LATEST).read_text())
        self.assertIn("need source reconciliation", (self.repo / "README.md").read_text())
        self.assertEqual((self.repo / "src/main.py").read_text(), secret + "\n")
        self.assertEqual((self.repo / "docs/architecture/raw/original.md").read_bytes(), original_raw)
        self.assertNotIn(secret, (self.repo / (RAW_PREFIX + target + ".md")).read_text())
        self.assertEqual(json.loads((self.repo / STATE).read_text())["code_baseline"], target)

    def test_handoff_only_push_links_recorded_context_without_staling_code(self):
        path = "docs/architecture/raw/new-agent-handoff.md"
        content = "# Handoff\n\n## Intent\nReduce duplicate delivery; actual device validation remains unrun.\n"
        self.write(path, content)
        self.commit("Capture handoff")
        self.run_update()
        self.assertIn(path, (self.repo / LATEST).read_text())
        self.assertIn("> Status: Current", (self.repo / "docs/architecture/wiki/context.md").read_text())
        self.assertEqual((self.repo / path).read_text(), content)

    def test_docs_only_push_has_no_update_and_does_not_create_evidence(self):
        self.write("README.md", (self.repo / "README.md").read_text() + "\nMore reading links.\n")
        self.commit("Edit generated entry point")
        result = self.run_update()
        self.assertFalse(result["changed"])
        self.assertFalse((self.repo / RAW_PREFIX).exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_range_catches_up_from_merged_baseline(self):
        self.write("src/first.py", "first\n")
        first = self.commit("First source change")
        self.write("src/second.py", "second\n")
        second = self.commit("Second source change")
        self.run_update()
        evidence = (self.repo / (RAW_PREFIX + second + ".md")).read_text()
        self.assertIn(first, evidence)
        self.assertIn(second, evidence)
        self.assertIn("src/first.py", evidence)
        self.assertIn("src/second.py", evidence)

    def test_rewriting_immutable_handoff_fails_before_mutation(self):
        self.write("docs/architecture/raw/original.md", "Rewritten original\n")
        self.commit("Rewrite evidence")
        with self.assertRaisesRegex(ValueError, "Immutable raw evidence changed"):
            self.run_update()
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_documentation_commit_after_sync_does_not_loop(self):
        self.write("src/main.py", "new source\n")
        self.commit("Change source")
        self.run_update()
        self.commit("Merge generated docs")
        evidence = list((self.repo / RAW_PREFIX).glob("*.md"))
        self.assertFalse(self.run_update()["changed"])
        self.assertEqual(list((self.repo / RAW_PREFIX).glob("*.md")), evidence)
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_dirty_checkout_is_preserved_and_rejected(self):
        self.write("src/main.py", "someone else's work\n")
        with self.assertRaisesRegex(ValueError, "clean checkout"):
            self.run_update()
        self.assertEqual((self.repo / "src/main.py").read_text(), "someone else's work\n")

    def test_unknown_baseline_fails_closed(self):
        self.write(STATE, json.dumps({"version": 1, "code_baseline": "0" * 40}))
        self.commit("Invalid baseline")
        with self.assertRaisesRegex(ValueError, "Git operation failed"):
            self.run_update()
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_markdown_runtime_skill_push_is_reconciled(self):
        self.write("skills/router/SKILL.md", "# Runtime skill\nNew routing contract.\n")
        target = self.commit("Change runtime skill")
        self.assertTrue(self.run_update()["changed"])
        self.assertIn("skills/router/SKILL.md", (self.repo / (RAW_PREFIX + target + ".md")).read_text())

    def test_owner_configuration_is_used_without_global_mentions(self):
        self.write("src/main.py", "new source\n")
        self.commit("Change source")
        result = self.run_update()
        self.assertIn("@fixture-owner", result["body"])
        self.assertNotIn("@mayankbohra", result["body"])
        self.assertEqual(result["reviewers"], ["fixture-reviewer"])

    def test_invalid_owner_config_fails_before_mutation(self):
        self.write(CONFIG, json.dumps({"version": 1, "source_roots": ["../outside"], "mentions": ["fixture-owner"], "reviewers": []}))
        self.commit("Invalid config")
        with self.assertRaisesRegex(ValueError, "Invalid monitored source root"):
            self.run_update()
        self.assertEqual(self.git("status", "--porcelain"), "")

    def exercise_publication(self, update, remote="https://github.com/example/mobile.git"):
        self.git("remote", "add", "origin", remote)
        actual_run = subprocess.run
        actual_command = publish.command
        published = []

        def run(args, **kwargs):
            if args[0] == "git" and "ls-remote" in args:
                return subprocess.CompletedProcess(args, 2, "", "")
            return actual_run(args, **kwargs)

        def command(args):
            if args[0] == "gh":
                if args[2] == "list":
                    return "[]"
                published.append((args, Path(args[args.index("--body-file") + 1]).read_text()))
                return "https://github.com/example/mobile/pull/1\n"
            if args[0] == "git" and "push" in args:
                published.append((args, ""))
                return ""
            return actual_command(args)

        previous = Path.cwd()
        try:
            os.chdir(self.repo)
            with patch.object(publish, "command", side_effect=command), patch.object(subprocess, "run", side_effect=run):
                with contextlib.redirect_stdout(io.StringIO()):
                    publish.publish(update, "example/mobile")
        finally:
            os.chdir(previous)
        return published

    def test_publication_creates_only_a_draft_targeting_main(self):
        self.write("src/main.py", "new source\n")
        self.commit("Change source")
        update = self.run_update()
        published = self.exercise_publication(update)
        pr, body = published[-1]
        self.assertIn("--draft", pr)
        self.assertEqual(pr[pr.index("--reviewer") + 1], "fixture-reviewer")
        self.assertEqual(pr[pr.index("--base") + 1], "main")
        self.assertIn("@fixture-owner", body)
        self.assertIn("automated documentation update", body)
        self.assertFalse(any("--force" in args or "-f" in args for args, _ in published))
        self.assertEqual((self.repo / "src/main.py").read_text(), "new source\n")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_actions_checkout_origin_without_git_suffix_can_publish(self):
        self.write("src/main.py", "new source\n")
        self.commit("Source push")
        update = self.run_update()
        published = self.exercise_publication(update, remote="https://github.com/example/mobile")
        self.assertIn("--draft", published[-1][0])

    def test_publication_refuses_unrelated_runtime_edits(self):
        self.write("src/main.py", "new source\n")
        self.commit("Change source")
        update = self.run_update()
        self.write("src/main.py", "unrelated pending runtime edit\n")
        with self.assertRaisesRegex(ValueError, "documentation scope"):
            self.exercise_publication(update)
        self.assertEqual((self.repo / "src/main.py").read_text(), "unrelated pending runtime edit\n")


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.config = {"version": 1, "source_roots": ["src"], "mentions": ["fixture-owner"], "reviewers": []}
        self.config_patch = patch.object(publish, "load_config", return_value=self.config)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.update = {"changed": True, "target": "a" * 40,
                       "branch": "automation/c5-docs-" + "a" * 12}

    def test_failed_pr_lookup_never_pushes_or_creates(self):
        with patch.object(publish, "command", side_effect=["https://github.com/example/mobile.git\n", ValueError("lookup failed")]) as command:
            with self.assertRaisesRegex(ValueError, "lookup failed"):
                publish.publish(self.update, "example/mobile")
        self.assertEqual([call.args[0][0] for call in command.call_args_list], ["git", "gh"])

    def test_another_origin_is_rejected_before_github_lookup(self):
        with patch.object(publish, "command", return_value="https://github.com/other/mobile.git") as command:
            with self.assertRaisesRegex(ValueError, "Origin does not match"):
                publish.publish(self.update, "example/mobile")
        self.assertEqual(command.call_count, 1)

    def test_existing_pr_is_preserved_without_a_push(self):
        with patch.object(publish, "command", side_effect=["https://github.com/example/mobile.git\n", '[{"url":"https://github.com/example/mobile/pull/1"}]']) as command:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                publish.publish(self.update, "example/mobile")
        self.assertIn("preserved without changes", output.getvalue())
        self.assertEqual(command.call_count, 2)


if __name__ == "__main__":
    unittest.main()
