"""Shared pytest configuration and fixtures."""

import sys
from unittest.mock import MagicMock

# Stub sounddevice before any transcriber.client import so tests don't
# require PortAudio system library.
if "sounddevice" not in sys.modules:
    sys.modules["sounddevice"] = MagicMock()
