"""Top-level orchestrator. Owns the agent registry and the REPL/self-improve loops."""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from jarvis.core.approval import ApprovalGate
from jarvis.core.bus import EventBus
from jarvis.core.config import Config
from jarvis.llm.client import LLMClient
from jarvis.memory.store import MemoryStore
from jarvis.agents.router import RouterAgent
from jarvis.agents.memory_agent import MemoryAgent
from jarvis.agents.planner import PlannerAgent
from jarvis.agents.coding import CodingAgent
from jarvis.agents.reflection import ReflectionAgent
from jarvis.agents.self_improvement import SelfImprovementAgent
from jarvis.selfimprove.loop import run_cycle

console = Console()


class Orchestrator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.bus = EventBus()
        self.approval = ApprovalGate(full_control=cfg.full_control)
        self.llm = LLMClient(cfg)
        self.memory = MemoryStore(cfg.data_dir)

        self.agents = {
            "memory": MemoryAgent(self.memory, self.llm),
            "planner": PlannerAgent(self.llm),
            "coding": CodingAgent(self.llm, self.approval, cfg.repo_path),
            "reflection": ReflectionAgent(self.llm, self.memory, self.bus),
            "selfimprove": SelfImprovementAgent(
                self.llm, self.approval, cfg.repo_path, self.bus
            ),
        }
        self.router = RouterAgent(self.llm, self.agents)

    # ---- doctor ----
    def doctor(self):
        backend, detail = self.llm.detect_backend()
        console.print(Panel(
            f"[bold]LLM backend:[/bold] {backend}\n{detail}\n"
            f"[bold]Repo:[/bold] {self.cfg.repo_path}\n"
            f"[bold]Data dir:[/bold] {self.cfg.data_dir}\n"
            f"[bold]Full control:[/bold] {self.cfg.full_control}\n"
            f"[bold]Voice:[/bold] {self.cfg.voice}",
            title="Jarvis Doctor",
            border_style="cyan",
        ))

    # ---- REPL ----
    def repl(self, voice: bool = False):
        console.print(Panel.fit(
            "[bold cyan]Jarvis online.[/bold cyan]\n"
            "Type your request. Commands: /quit /doctor /selfimprove /memory",
            border_style="cyan",
        ))
        if voice or self.cfg.voice:
            try:
                from jarvis.voice.loop import VoiceLoop
                VoiceLoop(self.cfg, self.handle).run()
                return
            except Exception as e:
                console.print(f"[yellow]Voice unavailable ({e}); falling back to text.[/yellow]")

        while True:
            try:
                user = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]bye.[/dim]")
                return
            if not user:
                continue
            if user in {"/quit", "/exit"}:
                return
            if user == "/doctor":
                self.doctor(); continue
            if user == "/selfimprove":
                self.self_improve(loop=False); continue
            if user == "/memory":
                console.print(self.memory.recent(10)); continue
            try:
                reply = self.handle(user)
                console.print(Panel(reply, title="jarvis", border_style="green"))
            except Exception as e:
                console.print(f"[red]error:[/red] {e}")

    def handle(self, user_text: str) -> str:
        self.memory.add_short("user", user_text)
        result = self.router.route(user_text)
        self.memory.add_short("jarvis", result)
        # Fire-and-forget reflection
        self.agents["reflection"].observe(user_text, result)
        return result

    # ---- self-improve ----
    def self_improve(self, loop: bool = False, target: str | None = None):
        agent: SelfImprovementAgent = self.agents["selfimprove"]
        run_cycle(agent, loop=loop, target=target)
