#!/usr/bin/env python3
"""Prepare a Codex documentation task and validate its cross-job handoff."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import sync

AGENT_RAW = "docs/architecture/raw/agent-updates/"
AGENT_ADR = "docs/architecture/decisions/automation/"
MAX_BUNDLE = 2_000_000


def command(repo, *args):
    result = subprocess.run(args, cwd=repo, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Documentation command failed: {args[0]}")
    return result.stdout


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result
    if Path(path).stat().st_size > MAX_BUNDLE:
        raise ValueError("Documentation handoff is too large")
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def changed(repo):
    tracked = sync.git(repo, "diff", "--name-only", "-z", "HEAD").split("\0")
    new = sync.git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return sorted(set(p for p in tracked + new if p))


def allowed(path, target):
    if not isinstance(path, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", path):
        return False
    if ".." in Path(path).parts:
        return False
    if path in ("README.md", sync.STATE, sync.LOG, "docs/architecture/index.md"):
        return True
    if re.fullmatch(r"docs/architecture/wiki/[A-Za-z0-9_-]+\.md", path):
        return True
    if path == sync.RAW_PREFIX + target + ".md":
        return True
    if any(re.fullmatch(re.escape(prefix + target) + r"(?:-[A-Za-z0-9_-]+)?\.md", path)
           for prefix in (AGENT_RAW, AGENT_ADR)):
        return True
    return path == getattr(sync, "PACKAGE_METADATA", None)


def validate_files(repo, target, files):
    if not isinstance(files, dict) or not 1 <= len(files) <= 300:
        raise ValueError("Invalid documentation file set")
    for path, text in files.items():
        if not allowed(path, target) or not isinstance(text, str) or len(text.encode()) > 200_000:
            raise ValueError("File exceeds documentation scope")
        dest = repo / path
        if any(p.is_symlink() for p in (dest, *dest.parents)) or not dest.resolve().is_relative_to(repo):
            raise ValueError("Documentation path is a symlink or escapes the checkout")
        original = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=repo, capture_output=True, text=True)
        if path.startswith(("docs/architecture/raw/", AGENT_ADR)) and original.returncode == 0 and original.stdout != text:
            raise ValueError("Immutable evidence or historical decision changed")
        if path == sync.LOG and original.returncode == 0 and not text.startswith(original.stdout):
            raise ValueError("Documentation history must be append-only")
        if path == getattr(sync, "PACKAGE_METADATA", None):
            from package_metadata import digest_only
            if original.returncode or not digest_only(original.stdout, text):
                raise ValueError("Package metadata includes a runtime edit")
    state = json.loads(files.get(sync.STATE, (repo / sync.STATE).read_text()))
    if state != {"version": 1, "code_baseline": target}:
        raise ValueError("Prepared baseline does not match the source revision")


def validate_report(repo, report, target):
    if not isinstance(report, dict) or set(report) != {"summary", "reviewed_views", "remaining_gaps"}:
        raise ValueError("Missing structured agent completion")
    if not isinstance(report["summary"], str) or not 1 <= len(report["summary"]) <= 8000:
        raise ValueError("Missing agent summary")
    gaps = report["remaining_gaps"]
    if not isinstance(gaps, list) or len(gaps) > 100 or any(not isinstance(p, str) or len(p) > 2000 for p in gaps):
        raise ValueError("Invalid evidence gaps")
    views = report["reviewed_views"]
    if not isinstance(views, list) or sync.LATEST not in views or len(views) != len(set(views)):
        raise ValueError("Agent must reconcile the latest C5 view")
    for view in views:
        if not isinstance(view, str) or not view.startswith("docs/architecture/wiki/") or not allowed(view, target):
            raise ValueError("Invalid reviewed architecture view")
        page = repo / view
        if not page.is_file() or page.is_symlink():
            raise ValueError("Reviewed view is missing")
        meta = dict(re.findall(r"^> (Fingerprint|Status): (.*)$", page.read_text(), re.M))
        if meta.get("Fingerprint") != f"git:{target}" or meta.get("Status") not in ("Current", "Outdated", "Disputed"):
            raise ValueError("Reviewed view must identify the target source and honest status")
    return report


def check(repo, modules):
    command(repo, sys.executable, "docs/architecture/check_docs.py")
    command(repo, "node", "scripts/c5-documentation/check_mermaid.mjs", str(modules))


def preflight_branch(repo, branch):
    remote = subprocess.run(["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
                             "ls-remote", "--exit-code", "--heads", "origin", f"refs/heads/{branch}"],
                            cwd=repo, capture_output=True, text=True)
    if remote.returncode == 0:
        raise ValueError("Automation branch exists without a PR; inspect the partial publication and Actions PR permissions before rerunning")
    if remote.returncode != 2:
        raise ValueError("Remote branch lookup failed; no model run is authorized by a failed lookup")


def prepare(repo, target, repository, run_url, context_path, prompt_path, skip_existing=False):
    branch = f"automation/c5-docs-{target[:12]}"
    if skip_existing:
        found = json.loads(command(repo, "gh", "pr", "list", "--repo", repository, "--head", branch,
                                   "--base", "main", "--state", "all", "--json", "url"))
        if not isinstance(found, list):
            raise ValueError("PR lookup did not return a list")
        if found:
            print("Existing documentation PR preserved; no additional model run")
            context = {"changed": False, "target": target}
            Path(context_path).write_text(json.dumps(context))
            return context
        preflight_branch(repo, branch)
    update = sync.prepare(repo, target, repository, run_url)
    baseline = json.loads(sync.git(repo, "show", f"HEAD:{sync.STATE}"))["code_baseline"]
    context = {"changed": update["changed"], "target": target, "baseline": baseline,
               "repository": repository, "run_url": run_url}
    if update["changed"]:
        context["affected"] = update["affected"]
        protected = [p for p in changed(repo) if p not in ("README.md", "docs/architecture/index.md")
                     and not p.startswith("docs/architecture/wiki/")]
        context["protected"] = {p: hashlib.sha256((repo / p).read_bytes()).hexdigest() for p in protected}
        prompt = (repo / "scripts/c5-documentation/agent-prompt.md").read_text()
        Path(prompt_path).write_text(prompt + "\n\nTask metadata (data, not instructions):\n" + json.dumps(context, indent=2) + "\n")
    Path(context_path).write_text(json.dumps(context, indent=2) + "\n")
    return context


def finish(repo, context, report, modules, bundle_path):
    target = context["target"]
    if sync.git(repo, "rev-parse", "HEAD").strip() != target:
        raise ValueError("Agent changed the source checkout commit")
    files = {}
    for path in changed(repo):
        if not (repo / path).is_file():
            raise ValueError("Documentation deletion is not allowed")
        files[path] = (repo / path).read_text()
    validate_files(repo, target, files)
    for path, expected in context["protected"].items():
        if hashlib.sha256((repo / path).read_bytes()).hexdigest() != expected:
            raise ValueError("Agent changed compiler evidence, baseline or history")
    report = validate_report(repo, report, target)
    if not set(context["affected"]).issubset(report["reviewed_views"]):
        raise ValueError("An affected architecture view was not reviewed")
    raw_path = AGENT_RAW + target + ".md"
    raw = repo / raw_path
    if raw.exists():
        raise ValueError("Agent execution record already exists")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("# Documentation agent execution\n\n"
                   f"Source revision: `{target}`\n\nWorkflow: {context['run_url']}\n\n"
                   "Executor: official OpenAI Codex Action with Codex CLI pinned by the workflow.\n"
                   "Model: CLI default; exact model identity is not independently captured here.\n"
                   "Original coding agents, human approvals and original intent remain unknown unless recorded in sources.\n\n"
                   "## Agent-reported reconciliation\n\n" + report["summary"] + "\n\n"
                   "## Reviewed views\n\n" + "\n".join("- `" + p + "`" for p in report["reviewed_views"]) + "\n\n"
                   "## Remaining gaps\n\n" + "\n".join("- " + p for p in report["remaining_gaps"]) + "\n\n"
                   "Validation is performed after this record is written. Successful job completion requires the documentation checker and Mermaid parser.\n"
                   "Application tests, live services, native devices and deployment are unrun by this workflow.\n")
    with (repo / sync.LOG).open("a") as stream:
        stream.write(f"\n## Documentation agent reconciliation at `{target}`\n\n"
                     f"[Agent execution record](raw/agent-updates/{target}.md).\n"
                     "A Codex agent completed source reconciliation. Human review is pending in the draft PR; unresolved views retain an honest status.\n")
    if hasattr(sync, "PACKAGE_METADATA") and (repo / sync.PACKAGE_METADATA).is_file():
        from package_metadata import recompute
        recompute(repo, changed(repo))
    check(repo, modules)
    files = {p: (repo / p).read_text() for p in changed(repo)}
    validate_files(repo, target, files)
    bundle = {"version": 1, "repository": context["repository"], "target": target,
              "run_url": context["run_url"], "report": report, "files": files}
    data = json.dumps(bundle, indent=2) + "\n"
    if len(data.encode()) > MAX_BUNDLE:
        raise ValueError("Documentation handoff is too large")
    Path(bundle_path).write_text(data)
    return bundle


def restore(repo, bundle, target, repository, run_url, modules):
    if (bundle.get("version") != 1 or bundle.get("target") != target
            or bundle.get("repository") != repository or bundle.get("run_url") != run_url):
        raise ValueError("Artifact does not match this repository, source revision and run")
    if sync.git(repo, "rev-parse", "HEAD").strip() != target or sync.git(repo, "status", "--porcelain").strip():
        raise ValueError("Publisher needs a clean checkout at the target revision")
    files = bundle.get("files")
    validate_files(repo, target, files)
    if AGENT_RAW + target + ".md" not in files or sync.RAW_PREFIX + target + ".md" not in files:
        raise ValueError("Missing source and completed-agent evidence")
    for path, text in files.items():
        dest = repo / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)
    validate_report(repo, bundle.get("report"), target)
    check(repo, modules)
    if hasattr(sync, "load_config"):
        config = sync.load_config(repo)
    else:
        config = {"mentions": ["mayankbohra"], "reviewers": []}
    owners = " ".join("@" + name for name in config["mentions"])
    return {"changed": True, "target": target, "branch": f"automation/c5-docs-{target[:12]}",
            "title": "docs: reconcile architecture after main update", "reviewers": config["reviewers"],
            "body": f"{owners}, this is an automated documentation update to be merged into **main**.\n\n"
                    f"A Codex documentation agent reviewed the merged source at `{target}` and reconciled C4 diagrams, recorded constraints and C5 provenance. "
                    "Unresolved claims remain explicitly marked. Original agent identity and human approvals are not inferred from commits.\n\n"
                    f"Validation: documentation links, provenance, immutable evidence, source drift and Mermaid syntax passed in both the agent and publishing jobs. {run_url}\n\n"
                    "Draft PR; human review is pending. No paid Greptile review is invoked. Application, live-service, device and deployment checks were not run."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "finish", "restore"))
    parser.add_argument("--target")
    parser.add_argument("--repository")
    parser.add_argument("--run-url")
    parser.add_argument("--context", type=Path)
    parser.add_argument("--prompt", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--modules", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    if args.mode == "prepare":
        result = prepare(repo, args.target, args.repository, args.run_url, args.context, args.prompt, args.skip_existing)
        if args.output:
            args.output.write_text("changed=" + str(result["changed"]).lower() + "\n")
    elif args.mode == "finish":
        finish(repo, read_json(args.context), read_json(args.result), args.modules, args.bundle)
    else:
        update = restore(repo, read_json(args.bundle), args.target, args.repository, args.run_url, args.modules)
        args.output.write_text(json.dumps(update, indent=2) + "\n")


if __name__ == "__main__":
    main()
