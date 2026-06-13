"""Run tests in the repo to validate a proposal."""
from __future__ import annotations

import subprocess
from pathlib import Path


def run_tests(repo_path: Path, timeout: int = 180) -> dict:
    """Run pytest. Returns {ok, returncode, output}."""
    try:
        p = subprocess.run(
            ["python", "-m", "pytest", "-q", "--maxfail=5"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "output": (p.stdout + p.stderr)[-4000:],
        }
    except FileNotFoundError:
        return {"ok": False, "returncode": 127, "output": "pytest not installed"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": 124, "output": "tests timed out"}
