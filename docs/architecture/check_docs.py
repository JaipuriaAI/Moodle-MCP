#!/usr/bin/env python3
"""Check the C4/C5 documentation contract with Python and local Git only.

Lexical grounding and source drift are signals for review, not semantic proof.
No application imports, secrets, network calls, or repository mutations occur.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


HEADER = re.compile(r"^> (Raw|Fingerprint|Monitored|Status): (.*)$", re.M)
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
NUMBER = re.compile(r"(?<![\w.,])\d[\d.,]*%?(?![\w.,])")
QUOTE = re.compile(r'["\u201c]([^"\u201d]{8,})["\u201d]')


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )


def prose(text: str) -> str:
    lines, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and not line.startswith(("#", ">")):
            lines.append(line)
    return "\n".join(lines)


def check(repo: Path) -> list[str]:
    docs = repo / "docs/architecture"
    raw = (docs / "raw").resolve()
    pages = sorted(docs.rglob("*.md"))
    issues = []
    if not pages:
        return ["no architecture documentation found"]
    readme = repo / "README.md"
    if readme.is_file():
        pages.insert(0, readme)
    tracked_raw = git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", "docs/architecture/raw")
    if tracked_raw.returncode != 0:
        issues.append("Git could not determine tracked raw evidence")
    else:
        for path in tracked_raw.stdout.splitlines():
            if not (repo / path).is_file():
                issues.append(f"{path}: tracked raw evidence removed; preserve the original")

    for page in pages:
        text = page.read_text()
        label = str(page.relative_to(repo))
        if sum(line.startswith("```") for line in text.splitlines()) % 2:
            issues.append(f"{label}: unbalanced code fences")
        for link in LINK.findall(text):
            if link.startswith(("https://", "http://", "mailto:", "#")):
                continue
            target = (page.parent / link.split("#", 1)[0]).resolve()
            if not target.is_relative_to(repo) or not target.exists():
                issues.append(f"{label}: missing or escaping relative link {link}")

        if page.is_relative_to(raw):
            committed = git(repo, "show", f"HEAD:{label}")
            if committed.returncode == 0 and committed.stdout != text:
                issues.append(f"{label}: tracked raw evidence changed; add a new record")

        if not page.is_relative_to(docs / "wiki"):
            continue
        meta = dict(HEADER.findall(text))
        for field in ("Raw", "Fingerprint", "Monitored", "Status"):
            if not meta.get(field):
                issues.append(f"{label}: missing {field} header")
        status = meta.get("Status")
        if status not in ("Current", "Outdated", "Disputed"):
            issues.append(f"{label}: unknown status {status!r}")
        raw_inputs = [
            (page.parent / link.split("#", 1)[0]).resolve()
            for link in LINK.findall(meta.get("Raw", ""))
        ]
        if not raw_inputs or any(
            not source.is_relative_to(raw) or not source.is_file()
            for source in raw_inputs
        ):
            issues.append(f"{label}: Raw must link existing immutable raw inputs")
        if status != "Current":
            continue

        sha = meta.get("Fingerprint", "").removeprefix("git:")
        paths = [p.strip() for p in meta.get("Monitored", "").split(",") if p.strip()]
        known = git(repo, "cat-file", "-e", f"{sha}^{{commit}}")
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or known.returncode != 0:
            issues.append(f"{label}: fingerprint is not an available full commit ID")
        elif paths:
            committed = git(repo, "diff", "--name-only", f"{sha}..HEAD", "--", *paths)
            working = git(repo, "diff", "--name-only", "HEAD", "--", *paths)
            untracked = git(repo, "ls-files", "--others", "--exclude-standard", "--", *paths)
            if any(r.returncode != 0 for r in (committed, working, untracked)):
                issues.append(f"{label}: Git could not determine source drift")
            elif any(r.stdout.strip() for r in (committed, working, untracked)):
                issues.append(f"{label}: monitored source drift; reconcile or mark outdated")
            for path in paths:
                target = (repo / path).resolve()
                if not target.is_relative_to(repo) or not target.exists():
                    issues.append(f"{label}: missing or escaping monitored path {path}")

        for sentence in re.split(r"(?<=[.!?])\s+", prose(text)):
            sources = []
            for link in LINK.findall(sentence):
                if "://" in link:
                    continue
                target = (page.parent / link.split("#", 1)[0]).resolve()
                if target.is_relative_to(raw) and target.is_file():
                    sources.append(target.read_text())
            bare = LINK.sub(" ", sentence)
            for number in NUMBER.findall(bare):
                exact = re.compile(r"(?<![\w.,])" + re.escape(number) + r"(?![\w.,])")
                if not any(exact.search(source) for source in sources):
                    issues.append(f"{label}: ungrounded figure {number!r}")
            for quote in QUOTE.findall(bare):
                if not any(quote in source for source in sources):
                    issues.append(f"{label}: ungrounded quotation {quote!r}")

        for diagram in re.findall(r"```mermaid\s*\n(.*?)```", text, re.S):
            if not re.search(r"^\s*C4(?:Context|Container|Component|Dynamic|Deployment)\b", diagram):
                continue
            aliases = re.findall(
                r"(?:Person|System|Container|Component)(?:_Ext|Db|Queue)?\s*\(\s*(\w+)\s*,",
                diagram,
            )
            if len(aliases) != len(set(aliases)):
                issues.append(f"{label}: duplicate C4 element alias")
            if len(aliases) > 20:
                issues.append(f"{label}: C4 view exceeds the small-view convention")
            for left, right in re.findall(r"\b(?:Rel(?:_[UDLR])?|BiRel)\(\s*(\w+)\s*,\s*(\w+)\s*,", diagram):
                if left not in aliases or right not in aliases:
                    issues.append(f"{label}: C4 relationship references an unknown element")

    return list(dict.fromkeys(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    repo = parser.parse_args().repo.resolve()
    issues = check(repo)
    for issue in issues:
        print(issue)
    print(f"Architecture documentation: {len(issues)} problem(s)")
    return bool(issues)


if __name__ == "__main__":
    sys.exit(main())
