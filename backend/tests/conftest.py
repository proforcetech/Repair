"""Shared test configuration to ensure core dependencies are loaded."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import core security early so that external dependencies like `jose`
# are loaded before any test attempts to stub them for optional environments.
from app.core import security  # noqa: F401
