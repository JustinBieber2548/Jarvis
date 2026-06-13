"""Voice loop: wake word → STT → Jarvis → TTS. Real libraries, graceful fallbacks."""
from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console

console = Console()


class VoiceLoop:
    def __init__(self, cfg, handle):
        self.cfg = cfg
        self.handle = handle
        self._import_or_die()

    def _import_or_die(self):
        try:
            import sounddevice  # noqa
            import numpy  # noqa
        except ImportError as e:
            raise RuntimeError(f"voice deps missing: {e} (pip install sounddevice numpy)")

    def run(self):
        import numpy as np
        import sounddevice as sd

        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError("faster-whisper not installed")

        try:
            import openwakeword
            from openwakeword.model import Model as WakeModel
            wake = WakeModel(wakeword_models=[self.cfg.wakeword])
            wake_enabled = True
        except Exception as e:
            console.print(f"[yellow]Wake-word unavailable ({e}); using push-to-talk (ENTER to record).[/yellow]")
            wake_enabled = False

        stt = WhisperModel("base", device="auto", compute_type="int8")
        console.print("[cyan]Voice loop ready.[/cyan]")

        sr = 16000
        while True:
            if wake_enabled:
                console.print(f"[dim]listening for '{self.cfg.wakeword}'...[/dim]")
                # Stream small chunks into wake model
                triggered = False
                with sd.InputStream(samplerate=sr, channels=1, dtype="int16") as stream:
                    while not triggered:
                        block, _ = stream.read(1280)
                        scores = wake.predict(block.flatten())
                        if any(v > 0.5 for v in scores.values()):
                            triggered = True
                console.print("[green]wake![/green]")
            else:
                try:
                    input("[ENTER to talk] ")
                except (EOFError, KeyboardInterrupt):
                    return

            # Record ~5s utterance
            console.print("[cyan]recording 5s...[/cyan]")
            audio = sd.rec(int(5 * sr), samplerate=sr, channels=1, dtype="int16")
            sd.wait()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                import wave
                with wave.open(tmp.name, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
                    wf.writeframes(audio.tobytes())
                wav_path = tmp.name

            segments, _ = stt.transcribe(wav_path, vad_filter=True)
            text = " ".join(s.text for s in segments).strip()
            os.unlink(wav_path)
            if not text:
                console.print("[dim](silence)[/dim]"); continue
            console.print(f"[bold]you:[/bold] {text}")
            reply = self.handle(text)
            console.print(f"[bold green]jarvis:[/bold green] {reply}")
            _speak(reply, self.cfg.piper_voice)


def _speak(text: str, voice: str):
    """Pipe text to Piper TTS if installed; otherwise system 'say' (mac) / espeak."""
    if shutil.which("piper"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                subprocess.run(
                    ["piper", "--model", voice, "--output_file", tmp.name],
                    input=text.encode("utf-8"), check=True,
                )
                _play(tmp.name); os.unlink(tmp.name)
                return
        except Exception as e:
            console.print(f"[yellow]piper failed: {e}[/yellow]")
    if shutil.which("say"):
        subprocess.run(["say", text]); return
    if shutil.which("espeak"):
        subprocess.run(["espeak", text]); return
    console.print("[dim](no TTS available — install piper, say, or espeak)[/dim]")


def _play(wav_path: str):
    for cmd in (["aplay", wav_path], ["afplay", wav_path], ["paplay", wav_path]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd); return
