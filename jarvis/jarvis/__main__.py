"""CLI entry point. `python -m jarvis` and `jarvis` script both land here."""
from __future__ import annotations

import typer
from rich.console import Console

from jarvis.core.config import Config
from jarvis.core.orchestrator import Orchestrator

app = typer.Typer(add_completion=False, help="Jarvis AI Operating System")
console = Console()


@app.command()
def chat(voice: bool = typer.Option(False, "--voice", help="Enable voice I/O")):
    """Interactive REPL (text by default, voice with --voice)."""
    cfg = Config.load()
    orch = Orchestrator(cfg)
    orch.repl(voice=voice)


@app.command()
def selfimprove(
    loop: bool = typer.Option(False, "--loop", help="Run continuously."),
    target: str = typer.Option("", "--target", help="File or hint to focus on."),
):
    """Run the self-improvement cycle."""
    cfg = Config.load()
    orch = Orchestrator(cfg)
    orch.self_improve(loop=loop, target=target or None)


@app.command()
def doctor():
    """Show environment status: LLM backend, voice, memory paths."""
    cfg = Config.load()
    Orchestrator(cfg).doctor()


def _default():
    """Allow `python -m jarvis` with no subcommand → chat."""
    import sys
    if len(sys.argv) == 1:
        sys.argv.append("chat")
    elif sys.argv[1] == "--voice":
        sys.argv[1:] = ["chat", "--voice"]
    app()


if __name__ == "__main__":
    _default()
