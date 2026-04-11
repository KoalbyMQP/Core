#!/usr/bin/env python3
"""
Desktop test harness for the ZaraOS startup UI.

Swaps in system_mock so the full setup flow can be exercised
on macOS / Linux desktop without wpa_cli, nerdctl, etc.

Usage:  uv run python src/test_desktop.py
"""

import sys
import importlib

# Swap the real system module for the mock BEFORE anything imports it
import system_mock
sys.modules["system"] = system_mock

# Now launch the real app
from main import main

if __name__ == "__main__":
    main()
