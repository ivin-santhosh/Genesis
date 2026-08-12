# -*- coding: utf-8 -*-
"""
Project Genesis - Intelligent Security Gateway (V1.0)
Non-negotiable permission and safety layer for internet access and system modifications.
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

# Security log file path
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
SECURITY_AUDIT_LOG = os.path.join(LOG_DIR, "security_audit.jsonl")

# Whitelist patterns for harmless read-only requests
HARMLESS_PATTERNS = [
    r"^https?://api\.duckduckgo\.com",
    r"^https?://html\.duckduckgo\.com",
    r"^https?://[a-z0-9\.\-]*wikipedia\.org",
    r"^https?://[a-z0-9\.\-]*pypi\.org",
    r"^https?://[a-z0-9\.\-]*github\.com/[a-zA-Z0-9\-_]+/[a-zA-Z0-9\-_]+/(raw|blob)/",
    r"^https?://docs\.",
    r"^https?://[a-z0-9\.\-]*readthedocs\.io",
]

# Sensitive patterns that require explicit user approval
SENSITIVE_PATTERNS = [
    r"^https?://[a-z0-9\.\-]*telegram\.org",
    r"^https?://[a-z0-9\.\-]*twitter\.com",
    r"^https?://[a-z0-9\.\-]*x\.com",
    r"^https?://[a-z0-9\.\-]*facebook\.com",
    r"^https?://[a-z0-9\.\-]*instagram\.com",
    r"^https?://[a-z0-9\.\-]*linkedin\.com",
    r"\.(zip|exe|bat|cmd|sh|ps1|msi|vbs)$",
]

# Always blocked patterns
BLOCKED_PATTERNS = [
    r"127\.0\.0\.1:(?!11434)",  # Block all local ports except Ollama (11434)
    r"localhost:(?!11434)",
    r"169\.254\.169\.254",       # Cloud metadata endpoints
    r"0\.0\.0\.0",
]


class SecurityGateway:
    """Intelligent Security Gateway governing all outward requests and state actions."""

    @staticmethod
    def log_audit(action_type: str, details: Dict[str, Any], status: str, rationale: str):
        """Append immutable JSON entry to security audit log."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "details": details,
            "status": status,
            "rationale": rationale,
        }
        try:
            with open(SECURITY_AUDIT_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logging.error(f"Failed to write security audit log: {e}")

    @classmethod
    def evaluate_web_request(cls, url: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        """
        Evaluates a web request URL and method.
        Returns (classification, reasoning):
        - "HARMLESS": Auto-passed
        - "SENSITIVE": Requires user confirmation
        - "BLOCKED": Instantly rejected
        """
        # 1. Check blocked patterns first
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                cls.log_audit("WEB_REQUEST", {"url": url, "method": method}, "BLOCKED", f"Matched blocked pattern: {pattern}")
                return "BLOCKED", f"Access to URL matching pattern '{pattern}' is permanently blocked for security isolation."

        # Non-GET requests (POST/PUT/DELETE) are automatically SENSITIVE unless blocked
        if method.upper() in ["POST", "PUT", "DELETE", "PATCH"]:
            cls.log_audit("WEB_REQUEST", {"url": url, "method": method}, "SENSITIVE", "State-mutating HTTP method requires user confirmation.")
            return "SENSITIVE", f"Request uses state-changing HTTP method ({method.upper()}). Requires direct user approval."

        # 2. Check harmless patterns
        for pattern in HARMLESS_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                cls.log_audit("WEB_REQUEST", {"url": url, "method": method}, "HARMLESS", f"Matched harmless pattern: {pattern}")
                return "HARMLESS", "Read-only request to verified public documentation or search engine."

        # 3. Check sensitive patterns
        for pattern in SENSITIVE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                cls.log_audit("WEB_REQUEST", {"url": url, "method": method}, "SENSITIVE", f"Matched sensitive pattern: {pattern}")
                return "SENSITIVE", f"Target URL matches sensitive domain/file category ({pattern}). Requires user verification."

        # 4. Default for unknown external GET requests: SENSITIVE for complete transparency
        cls.log_audit("WEB_REQUEST", {"url": url, "method": method}, "SENSITIVE", "Default transparent evaluation for unclassified URL.")
        return "SENSITIVE", "Target URL is outside the pre-approved harmless whitelist. Requires user authorization."


security_gateway = SecurityGateway()
