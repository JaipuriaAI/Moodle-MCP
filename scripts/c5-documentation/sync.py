#!/usr/bin/env python3
"""Compile source-backed C5 evidence; flag C4 drift without inventing rationale."""

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo


STATE = "docs/architecture/automation-state.json"
LATEST = "docs/architecture/wiki/c5-latest.md"
LOG = "docs/architecture/log.md"
RAW_PREFIX = "docs/architecture/raw/automation/"
BEGIN = "<!-- c5-status:start -->"
END = "<!-- c5-status:end -->"
GENERATED = {STATE, LATEST, LOG, "README.md", "docs/architecture/index.md"}
CONFIG = "scripts/c5-documentation/config.json"


def load_config(repo):
    config = json.loads((Path(repo) / CONFIG).read_text())
    roots = config.get("source_roots")
    if config.get("version") != 1 or not isinstance(roots, list) or not roots:
        raise ValueError("Invalid documentation configuration")
    for root in roots:
        if (not isinstance(root, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", root)
                or ".." in Path(root).parts):
            raise ValueError("Invalid monitored source root")
    for field in ("mentions", "reviewers"):
        values = config.get(field)
        if (not isinstance(values, list) or (field == "mentions" and not values)
                or any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", v) for v in values)):
            raise ValueError("Invalid documentation owners")
    return config


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Local Git operation failed: {' '.join(args)}")
    return result.stdout


def output_path(path):
    return path in GENERATED or path.startswith((RAW_PREFIX, "docs/architecture/raw/agent-updates/", "docs/architecture/decisions/automation/", "docs/architecture/wiki/"))


def handoff_path(path):
    return path.endswith(".md") and path.startswith("docs/architecture/raw/") and not path.startswith(RAW_PREFIX)


def relevant(path):
    if output_path(path) or path.startswith(("scripts/c5-documentation/", ".agents/skills/c4-architecture/", ".agents/skills/architecture-decision-records/", ".agents/skills/grounded-vault/")):
        return False
    if path in ("skills-lock.json", ".github/workflows/c5-documentation.yml", "docs/architecture/check_docs.py", "docs/architecture/index.md", "docs/architecture/CONVENTION.md", "docs/architecture/automation.md"):
        return False
    return not path.startswith("docs/architecture/templates/")


def changed_paths(repo, base, target, *paths):
    return [p for p in git(repo, "diff", "--name-only", "-z", base, target, "--", *paths).split("\0") if p]


def source_link(repository, revision, path):
    return f"https://github.com/{repository}/blob/{revision}/{quote(path, safe='/')}"


def prepare(repo, target, repository, run_url):
    repo = Path(repo).resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", target):
        raise ValueError("Target must be an exact commit ID")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository identity")
    if run_url and not re.fullmatch(rf"https://github\.com/{re.escape(repository)}/actions/runs/\d+", run_url):
        raise ValueError("Run URL must identify this repository's Actions run")
    if git(repo, "rev-parse", "HEAD").strip() != target:
        raise ValueError("Checkout must match the target commit")
    if git(repo, "status", "--porcelain").strip():
        raise ValueError("Reconciliation requires a clean checkout; preserve local work")

    config = load_config(repo)
    state = json.loads((repo / STATE).read_text())
    baseline = state["code_baseline"]
    if state.get("version") != 1 or not re.fullmatch(r"[0-9a-f]{40}", baseline):
        raise ValueError("Unknown or invalid reconciliation state")
    git(repo, "merge-base", "--is-ancestor", baseline, target)
    paths = [p for p in changed_paths(repo, baseline, target) if relevant(p)]
    if not paths:
        return {"changed": False, "target": target}
    if any(re.search(r"[\r\n`<>\[\]]", p) for p in paths):
        raise ValueError("Changed path needs manual Markdown escaping")
    handoffs = [p for p in paths if handoff_path(p)]
    for path in handoffs:
        original = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{baseline}:{path}"], capture_output=True)
        if original.returncode == 0:
            raise ValueError("Immutable raw evidence changed; add a new handoff record")

    affected = []
    for page in sorted((repo / "docs/architecture/wiki").glob("*.md")):
        if page.name == "c5-latest.md":
            continue
        text = page.read_text()
        fields = dict(re.findall(r"^> (Fingerprint|Monitored|Status): (.*)$", text, re.M))
        fingerprint = fields.get("Fingerprint", "").removeprefix("git:")
        if not re.fullmatch(r"[0-9a-f]{40}", fingerprint):
            raise ValueError(f"Missing valid source fingerprint: {page.name}")
        monitored = [p.strip() for p in fields.get("Monitored", "").split(",") if p.strip()]
        if not monitored:
            raise ValueError(f"Missing monitored source paths: {page.name}")
        drift = changed_paths(repo, fingerprint, target, *monitored)
        if fields.get("Status") in ("Current", "Outdated") and drift:
            affected.append(page.relative_to(repo).as_posix())

    captured = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")
    raw_path = RAW_PREFIX + target + ".md"
    raw = repo / raw_path
    if raw.exists():
        raise ValueError("Raw snapshot already exists; do not overwrite evidence")
    commits = git(repo, "rev-list", "--reverse", f"{baseline}..{target}").splitlines()
    snapshot = ["# Automated main-push evidence", "", f"Captured: {captured}",
                f"Previous baseline: `{baseline}`", f"Target code revision: `{target}`",
                f"Workflow: {run_url or 'local validation; no remote run established'}", "",
                "Executor: GitHub Actions source compiler. No language model was invoked.",
                "Original coding-agent/model identity and human approvals are not inferred from commits.", "",
                "## Commits in the reconciled range", ""]
    snapshot += [f"- [{sha}](https://github.com/{repository}/commit/{sha})" for sha in commits]
    snapshot += ["", "## Changed inputs", ""]
    for path in paths:
        revision = target if (repo / path).exists() else baseline
        snapshot.append(f"- [`{path}`]({source_link(repository, revision, path)})")
    snapshot += ["", "## Captured context", ""]
    if handoffs:
        snapshot += [f"- [Captured raw record: {p}]({source_link(repository, target, p)})" for p in handoffs]
        snapshot.append("These records are sources of intent and verification; a linked claim is not independently rerun proof.")
    else:
        snapshot.append("No new coding-agent handoff was found. Original intent, rejected alternatives and agent identity remain unknown.")
    decisions = [p for p in paths if p.startswith("docs/architecture/decisions/") and (repo / p).exists()]
    snapshot += [f"- [Recorded decision: {p}]({source_link(repository, target, p)})" for p in decisions]
    snapshot += ["", "## Architecture requiring semantic review", ""]
    snapshot += [f"- `{p}`" for p in affected] or ["No monitored architecture view changed in this reconciliation."]
    snapshot += ["", "## Validation boundary", "",
                 "The workflow runs the local documentation checker before publishing. Application tests and live services are not exercised.",
                 "Semantic architecture review remains necessary for affected views. This compilation does not establish deployment or a completed agent review.", ""]
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("\n".join(snapshot))

    for path in affected:
        page = repo / path
        text = page.read_text()
        text = re.sub(r"^> Status: Current$", "> Status: Outdated", text, flags=re.M)
        marker = "<!-- c5-drift -->"
        text = text.split(marker, 1)[0].rstrip()
        text += f"\n\n{marker}\nMonitored source changed; reconcile this view before treating it as current.\nSee [push evidence](../raw/automation/{target}.md).\n"
        page.write_text(text)

    monitored = [p for p in config["source_roots"] if (repo / p).exists()]
    if not monitored:
        raise ValueError("No source roots are available for the compiled change view")
    source = f"../raw/automation/{target}.md"
    latest = ["# C5: latest main-push reconciliation", "",
              f"> Raw: [push evidence]({source})", f"> Fingerprint: git:{target}",
              f"> Monitored: {', '.join(monitored)}", "> Status: Current", "",
              "This is source reconciliation performed by a deterministic compiler.",
              "It records merged inputs and available context; it is not an AI interpretation of architecture.", "",
              "## Intent, decisions and agent provenance", ""]
    if handoffs or decisions:
        latest += [f"- [Captured context: {p}]({source_link(repository, target, p)})" for p in handoffs + decisions]
        latest.append(f"Consult those records for intent, alternatives and actual checks ([evidence]({source})).")
    else:
        latest.append(f"No new handoff was captured. Original reasoning, agent/model attribution and individual approvals remain unknown ([evidence]({source})).")
    latest += ["", "## Architecture status and next safe action", ""]
    latest += [f"- [{Path(p).stem}]({Path(p).name}): source changed; semantic reconciliation needed." for p in affected]
    if not affected:
        latest.append("The monitored architecture views have no source drift at this target.")
    latest += ["", f"Review the merged range and the recorded context in [push evidence]({source}).",
               "Reconcile affected diagrams and decisions using the convention, then record actual validation.",
               "Live-service, integration and deployment outcomes remain unverified by this workflow.", ""]
    (repo / LATEST).write_text("\n".join(latest))
    (repo / STATE).write_text(json.dumps({"version": 1, "code_baseline": target}, indent=2) + "\n")
    with (repo / LOG).open("a") as stream:
        stream.write(f"\n## {captured} - automated main-push reconciliation\n\nCode baseline: `{target}`.\n\n[Captured inputs](raw/automation/{target}.md) and [latest C5 record](wiki/c5-latest.md).\n")
        stream.write("Affected architecture views are marked outdated pending semantic review. The documentation checker runs before PR publication; application/live-service checks are unrun.\n")

    readme = repo / "README.md"
    text = readme.read_text()
    if text.count(BEGIN) != 1 or text.count(END) != 1 or text.index(BEGIN) > text.index(END):
        raise ValueError("README status markers are missing or ambiguous")
    message = "Architecture views need source reconciliation." if affected else "Monitored architecture views have no source drift."
    status = f"{BEGIN}\n**Documentation status:** {message} See the [latest C5 evidence](docs/architecture/wiki/c5-latest.md).\n{END}"
    start, rest = text.split(BEGIN)
    _, end = rest.split(END)
    readme.write_text(start + status + end)

    modified = git(repo, "diff", "--name-only", "HEAD").splitlines()
    modified += git(repo, "ls-files", "--others", "--exclude-standard").splitlines()
    if any(not output_path(p) for p in modified):
        raise ValueError("Reconciliation touched a file outside its documentation scope")
    checked = subprocess.run(["python", str(repo / "docs/architecture/check_docs.py")], cwd=repo)
    if checked.returncode:
        raise ValueError("Generated documentation failed validation; publication is blocked")
    owners = " ".join("@" + owner for owner in config["mentions"])
    body = (f"{owners} - this is an automated documentation update to be merged into **main**.\n\n"
            f"Reconciles merged inputs from `{baseline}` through `{target}` into C5 evidence and captured handoff links. "
            "Affected architecture views are marked outdated for semantic review; source values and application secrets are not copied.\n\n"
            f"Validation: documentation links, provenance headers, source drift and raw-evidence checks passed. {run_url}\n\n"
            "Opened as a draft per the requested review policy; no paid reviewer is invoked by this workflow. Application and live-integration checks were not run by this workflow.")
    return {"changed": True, "target": target, "branch": f"automation/c5-docs-{target[:12]}",
            "title": "docs: automated C5 documentation update", "baseline": baseline, "affected": affected, "body": body, "reviewers": config["reviewers"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--target", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-url", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.repo, args.target, args.repository, args.run_url)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Documentation update prepared" if result["changed"] else "No new documentation inputs")


if __name__ == "__main__":
    main()
