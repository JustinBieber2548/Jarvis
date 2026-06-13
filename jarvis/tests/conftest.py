"""pytest conftest — add jarvis package to sys.path."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
