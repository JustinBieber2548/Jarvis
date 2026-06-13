"""Apply a proposal in a git branch sandbox; run tests; merge on approval."""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


def _run(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)[-4000:]
    except FileNotFoundError as e:
        return 127, str(e)
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def _has_git(repo: Path) -> bool:
    return (repo / ".git").exists()


def apply_proposal(repo_path: Path, proposal: dict) -> dict:
    """Apply proposal in-place (no git): used as fallback when no .git present.
    Returns report dict."""
    changes = proposal.get("changes", [])
    written = []
    backups: dict[str, str | None] = {}
    for ch in changes:
        target = repo_path / ch["path"]
        backups[ch["path"]] = target.read_text(encoding="utf-8") if target.exists() else None
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(ch["new_content"], encoding="utf-8")
        written.append(ch["path"])
    return {"written": written, "backups": backups, "branch": None}


def revert(repo_path: Path, report: dict):
    for path, original in report.get("backups", {}).items():
        target = repo_path / path
        if original is None:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        else:
            target.write_text(original, encoding="utf-8")


def git_apply_proposal(repo_path: Path, proposal: dict) -> dict:
    """Apply on a fresh branch. Returns report with branch name + diff."""
    if not _has_git(repo_path):
        report = apply_proposal(repo_path, proposal)
        report["mode"] = "filesystem"
        return report

    branch = f"jarvis/self-improve/{int(time.time())}"
    code, out = _run(["git", "checkout", "-b", branch], repo_path)
    if code != 0:
        return {"error": f"git checkout failed: {out}", "branch": None, "mode": "git"}

    written = []
    for ch in proposal.get("changes", []):
        target = repo_path / ch["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(ch["new_content"], encoding="utf-8")
        written.append(ch["path"])

    _run(["git", "add"] + written, repo_path)
    diff_code, diff = _run(["git", "diff", "--cached"], repo_path)
    return {"branch": branch, "written": written, "diff": diff, "mode": "git"}


def git_finalize(repo_path: Path, branch: str, message: str, merge: bool) -> dict:
    _run(["git", "commit", "-m", message], repo_path)
    if not merge:
        return {"committed": True, "merged": False, "branch": branch}
    # Switch back to previous branch (main/master) and merge
    code, out = _run(["git", "symbolic-ref", "--short", "HEAD"], repo_path)
    code, default = _run(["git", "for-each-ref", "--format=%(refname:short)",
                          "refs/heads/main"], repo_path)
    default_branch = "main" if default.strip() else "master"
    _run(["git", "checkout", default_branch], repo_path)
    mcode, mout = _run(["git", "merge", "--no-ff", branch, "-m", f"Merge {branch}"], repo_path)
    return {"committed": True, "merged": mcode == 0, "branch": branch, "merge_output": mout}


def git_abort(repo_path: Path, branch: str):
    if not branch or not _has_git(repo_path):
        return
    _run(["git", "checkout", "-"], repo_path)
    _run(["git", "branch", "-D", branch], repo_path)
