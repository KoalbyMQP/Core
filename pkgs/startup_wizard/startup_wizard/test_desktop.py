#!/usr/bin/env python3
"""
Desktop test harness for the ZaraOS startup UI.

Swaps in system_mock so the full setup flow can be exercised
on macOS / Linux desktop without wpa_cli, nerdctl, etc.

Usage:  python -m startup_wizard.test_desktop
"""

import sys

# Swap the real system module for the mock BEFORE anything imports it
from startup_wizard import system_mock
sys.modules["system"] = system_mock

# Now launch the real app (with ROS2 disabled since we're in mock mode)
from startup_wizard.main import main

if __name__ == "__main__":
    main()
