# Jarvis AI Operating System

A local-first, self-improving AI companion. Python-only. No Lovable dependency required to run.

> **Status**: Phase 1 + early Phase 5 core. Voice, memory, agents, and the self-improvement loop work. Computer control is wired but gated behind approval.

## Quick start

```bash
cd jarvis
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m jarvis            # interactive shell
```

### Run modes

| Command                              | What it does                                          |
| ------------------------------------ | ----------------------------------------------------- |
| `python -m jarvis`                   | Interactive text REPL                                 |
| `python -m jarvis --voice`           | Voice mode (wake word + STT + TTS)                    |
| `python -m jarvis selfimprove`       | Run one self-improvement cycle (propose → approve)    |
| `python -m jarvis selfimprove --loop`| Continuous self-improvement (still asks before merge) |
| `python -m jarvis doctor`            | Check environment / what's missing                    |

## LLM backend (auto-detected)

1. **Ollama** at `http://localhost:11434` (free, local). Pull a model: `ollama pull llama3.1`.
2. **OpenAI-compatible** fallback. Set in `.env`:
   ```
   OPENAI_API_BASE=https://api.openai.com/v1
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   ```
   (Works with OpenAI, Groq, OpenRouter, LM Studio, vLLM, Ollama's `/v1`.)

Run `python -m jarvis doctor` to see which backend Jarvis picked.

## Architecture

```
jarvis/
  core/         orchestrator, config, approval gate, event bus
  agents/       router, planner, coding, research, reflection, self_improvement
  memory/       SQLite + ChromaDB (short/long/episodic/semantic)
  llm/          unified LLM client (Ollama + OpenAI-compatible)
  voice/        Whisper STT + Piper TTS + OpenWakeWord
  desktop/      PyAutoGUI wrapper (approval-gated)
  selfimprove/  patch proposer, sandbox runner, git applier
  tools/        web search, file ops, shell (approval-gated)
```

## Self-improvement loop

1. Reflection agent or user nominates an improvement target.
2. Coding agent generates a unified diff against the repo.
3. Patch is applied to a fresh `jarvis/self-improve/<timestamp>` git branch.
4. Tests run (`pytest`). Diff + test report shown.
5. You approve (y/N). On approval, branch is merged into `main`.
6. If `JARVIS_FULL_CONTROL=1`, branch is auto-merged after tests pass — still asks for the very first time per session.

## Approval gate

Every action with a non-`safe` risk level prompts you. CLI shows:

```
Jarvis would like to perform the following action. Approve? [y/N]
  Action:  apply_patch
  Target:  jarvis/agents/router.py
  Risk:    medium
```

Categories: `code_change`, `file_delete`, `deploy`, `browser`, `desktop`, `self_modify`.

## Packaging as `.exe`

```bash
pip install pyinstaller
pyinstaller --onefile --name Jarvis -m jarvis
# dist/Jarvis(.exe) — add to OS startup for auto-launch.
```

## Tests

```bash
pytest -q
```
