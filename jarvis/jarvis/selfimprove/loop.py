"""Self-improvement cycle: propose → apply → test → diff → approve → merge."""
from __future__ import annotations

import time

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from jarvis.core.approval import ActionRequest, Risk
from jarvis.selfimprove.git_apply import (
    git_apply_proposal, git_finalize, git_abort, revert, apply_proposal,
)
from jarvis.selfimprove.sandbox import run_tests

console = Console()


def run_cycle(agent, loop: bool = False, target: str | None = None) -> None:
    while True:
        _one(agent, target)
        if not loop:
            return
        console.print("[dim]sleeping 30s before next cycle...[/dim]")
        time.sleep(30)


def _one(agent, target: str | None):
    console.rule("[bold cyan]Self-improvement cycle")
    console.print("Proposing improvement...")
    try:
        proposal = agent.propose(target)
    except Exception as e:
        console.print(f"[red]Proposal failed:[/red] {e}")
        return

    title = proposal.get("title", "(untitled)")
    rationale = proposal.get("rationale", "")
    changes = proposal.get("changes", [])

    console.print(Panel(
        f"[bold]{title}[/bold]\n\n{rationale}\n\nFiles: {[c['path'] for c in changes]}",
        title="Proposal", border_style="cyan",
    ))

    if not changes:
        console.print("[yellow]No changes proposed. Skipping.[/yellow]")
        agent.bus.publish("selfimprove.noop", {"title": title})
        return

    ok, why = agent.validate(proposal)
    if not ok:
        console.print(f"[red]Validation failed:[/red] {why}")
        return

    # Apply to git branch (or filesystem fallback)
    report = git_apply_proposal(agent.repo_path, proposal)
    if "error" in report:
        console.print(f"[red]{report['error']}[/red]")
        return

    if report.get("mode") == "git" and report.get("diff"):
        console.print(Panel(
            Syntax(report["diff"][:6000], "diff", line_numbers=False),
            title=f"Diff on branch {report['branch']}", border_style="magenta",
        ))

    # Run tests
    console.print("Running tests...")
    test_report = run_tests(agent.repo_path)
    color = "green" if test_report["ok"] else "red"
    console.print(Panel(
        test_report["output"] or "(no output)",
        title=f"Tests {'PASSED' if test_report['ok'] else 'FAILED'} (rc={test_report['returncode']})",
        border_style=color,
    ))

    # Decide
    auto_merge = agent.approval.full_control and test_report["ok"]
    approved = auto_merge
    if not auto_merge:
        approved = agent.approval.request(ActionRequest(
            action="merge_self_improvement",
            target=report.get("branch") or "<filesystem>",
            risk=Risk.HIGH if not test_report["ok"] else Risk.MEDIUM,
            category="self_modify",
            details=f"{title}\nTests: {'pass' if test_report['ok'] else 'FAIL'}",
        ))

    if approved:
        if report.get("mode") == "git" and report.get("branch"):
            final = git_finalize(agent.repo_path, report["branch"],
                                 message=f"jarvis: {title}", merge=True)
            console.print(f"[green]Merged.[/green] {final}")
        else:
            console.print("[green]Applied (no git).[/green]")
        agent.bus.publish("selfimprove.applied", {"title": title})
    else:
        if report.get("mode") == "git" and report.get("branch"):
            git_abort(agent.repo_path, report["branch"])
            console.print("[yellow]Aborted; branch deleted.[/yellow]")
        else:
            revert(agent.repo_path, report)
            console.print("[yellow]Reverted filesystem changes.[/yellow]")
        agent.bus.publish("selfimprove.rejected", {"title": title})
