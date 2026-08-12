# -*- coding: utf-8 -*-
"""
Project Genesis - Remote Power Manager & WOL Handler (V1.0)
Manages power configuration (prevent sleep-after-wake), Wake-on-LAN commands, and graceful OS shutdown.
"""

import logging
import os
import subprocess
import sys
from typing import Tuple

try:
    from wakeonlan import send_magic_packet
    _WOL = True
except ImportError:
    _WOL = False


def configure_power_settings() -> Tuple[bool, str]:
    """
    Configures Windows Power Management to prevent sleep after Wake-on-LAN (System Unattended Sleep Timeout = 0)
    and ensures closing lid does nothing on AC/Battery.
    """
    if sys.platform != "win32":
        return False, "Power configuration powercfg is Windows-specific."

    commands = [
        # Disable System Unattended Sleep Timeout (AC)
        "powercfg /SETACVALUEINDEX SCHEME_CURRENT 238C9FA8-0AAD-41ED-83F4-97BE242C8F20 7bc4a2f9-d8fc-4469-b07b-33eb785aaca0 0",
        # Disable System Unattended Sleep Timeout (DC/Battery)
        "powercfg /SETDCVALUEINDEX SCHEME_CURRENT 238C9FA8-0AAD-41ED-83F4-97BE242C8F20 7bc4a2f9-d8fc-4469-b07b-33eb785aaca0 0",
        # Close lid = Do nothing (AC)
        "powercfg /SETACVALUEINDEX SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e36005004cd 5ca83367-6e45-459f-a27b-476b1d01c936 0",
        # Close lid = Do nothing (DC/Battery)
        "powercfg /SETDCVALUEINDEX SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e36005004cd 5ca83367-6e45-459f-a27b-476b1d01c936 0",
        # Apply current scheme
        "powercfg /SETACTIVE SCHEME_CURRENT"
    ]

    try:
        for cmd in commands:
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "Power management configured: Unattended sleep disabled & lid-close set to 'Do nothing'."
    except Exception as e:
        return False, f"Power management configuration warning: {e}"


def send_wol_packet(mac_address: str) -> Tuple[bool, str]:
    """Sends Wake-on-LAN magic packet to specified MAC address."""
    if not _WOL:
        return False, "wakeonlan package is not installed."
    try:
        send_magic_packet(mac_address)
        return True, f"Wake-on-LAN magic packet sent to MAC address: {mac_address}"
    except Exception as e:
        return False, f"Failed to send Wake-on-LAN magic packet: {e}"


def graceful_remote_shutdown(delay_seconds: int = 10) -> Tuple[bool, str]:
    """Gracefully shuts down the host OS after a safety delay."""
    if sys.platform != "win32":
        return False, "Remote shutdown command currently supports Windows OS."

    try:
        cmd = f'shutdown /s /t {delay_seconds} /c "Genesis Telegram Remote Shutdown Initiated"'
        subprocess.run(cmd, shell=True, check=True)
        return True, f"Host OS graceful shutdown initiated. System will power off in {delay_seconds} seconds."
    except Exception as e:
        return False, f"Shutdown command execution failed: {e}"
