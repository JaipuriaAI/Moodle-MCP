#!/usr/bin/env python3
"""Publish only validated documentation as a draft PR; never merge or force-push."""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from sync import load_config, output_path


def command(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(f"Command failed: {args[0]} {args[1]}")
    return result.stdout


def publish(update, repository):
    if update.get("changed") is False:
        print("No new documentation inputs; no PR needed")
        return
    target = update.get("target", "")
    branch = update.get("branch", "")
    if update.get("changed") is not True or not re.fullmatch(r"[0-9a-f]{40}", target):
        raise ValueError("Invalid prepared update")
    if branch != f"automation/c5-docs-{target[:12]}":
        raise ValueError("Unexpected automation branch")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository identity")
    config = load_config(Path.cwd())
    if update.get("reviewers", []) != config["reviewers"]:
        raise ValueError("Prepared reviewers do not match repository owners")
    expected_remote = f"https://github.com/{repository}.git"
    remote_url = command(["git", "remote", "get-url", "origin"]).strip()
    if remote_url not in (expected_remote, expected_remote.removesuffix(".git")):
        raise ValueError("Origin does not match this repository")
    prs = json.loads(command(["gh", "pr", "list", "--repo", repository, "--head", branch,
                             "--base", "main", "--state", "all", "--json", "url"]))
    if not isinstance(prs, list):
        raise ValueError("GitHub PR lookup did not return a list")
    if prs:
        print(f"A documentation PR already exists: {prs[0]['url']}; preserved without changes")
        return
    if command(["git", "rev-parse", "HEAD"]).strip() != target:
        raise ValueError("Source checkout changed after reconciliation")
    remote = subprocess.run(["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
                             "ls-remote", "--exit-code", "--heads", "origin", f"refs/heads/{branch}"],
                            capture_output=True, text=True)
    if remote.returncode != 2:
        raise ValueError("Branch exists or remote lookup failed; inspect it before publishing")
    modified = command(["git", "diff", "--name-only", "HEAD"]).splitlines()
    modified += command(["git", "ls-files", "--others", "--exclude-standard"]).splitlines()
    if not modified or any(not output_path(p) for p in modified):
        raise ValueError("Prepared changes exceed documentation scope or are empty")
    command(["python", "docs/architecture/check_docs.py"])
    command(["git", "switch", "-c", branch])
    command(["git", "add", "--", *modified])
    command(["git", "-c", "user.name=github-actions[bot]",
             "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
             "commit", "-m", update["title"]])
    command(["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential",
             "push", "origin", f"HEAD:refs/heads/{branch}"])
    with tempfile.TemporaryDirectory(prefix="c5-pr-") as folder:
        body = Path(folder) / "body.md"
        body.write_text(update["body"])
        args = ["gh", "pr", "create", "--draft", "--repo", repository,
                       "--base", "main", "--head", branch, "--title", update["title"],
                       "--body-file", str(body)]
        for reviewer in config["reviewers"]:
            args.extend(["--reviewer", reviewer])
        url = command(args)
    print(url.strip())


if __name__ == "__main__":
    publish(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2])
