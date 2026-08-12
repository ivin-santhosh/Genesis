# -*- coding: utf-8 -*-
"""
Project Genesis - Cloud Relay Proxy (V1.0)
Stateless fallback relay for Webhook forwarding & remote WOL trigger.
Holds zero state, zero user data, zero LLM code.
"""

import json
import logging
import os
import requests
from typing import Dict, Any


class CloudRelayProxy:
    """Stateless fallback proxy to verify local bot availability and trigger WOL."""

    def __init__(self, local_bot_url: str = "http://localhost:8080"):
        self.local_bot_url = local_bot_url

    def ping_local_bot(self) -> bool:
        """Pings local Genesis interface to verify active status."""
        try:
            resp = requests.get(f"{self.local_bot_url}/health", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def handle_webhook_forward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Forwards incoming Telegram update to local bot endpoint if active."""
        if self.ping_local_bot():
            try:
                resp = requests.post(f"{self.local_bot_url}/webhook", json=payload, timeout=5.0)
                return {"status": "forwarded", "code": resp.status_code}
            except Exception as e:
                return {"status": "failed", "reason": str(e)}
        return {"status": "local_bot_offline", "action_suggested": "WOL"}


cloud_relay = CloudRelayProxy()
