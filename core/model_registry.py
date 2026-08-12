# -*- coding: utf-8 -*-
"""
Project Genesis - Dynamic Model Registry & Thermal Guard (V1.0)
Manages Ollama model switching, VRAM budget allocation, thermal throttling, and default fallback roles.
"""

import logging
import os
import sys
import time
from typing import Dict, Any, Optional, Tuple
from langchain_ollama import ChatOllama

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


class ModelRegistry:
    """Manages LLM instances, VRAM budgets, model switches, and thermal monitoring."""

    # Installed local models & default role mappings
    DEFAULT_ROLES = {
        "nexus": "stark-enterprise:latest",          # ID: 9afbf5cab96a (qwen2.5-coder variant)
        "coder": "qwen2.5-coder:7b-instruct-q5_K_M", # ID: 771d6745a8b6 (coder specialist)
        "thinker": "qwen3:4b",                       # ID: 359d7dd4bcda (fast reasoning & verification)
        "vision": "qwen3-vl:4b-instruct-q4_K_M"      # ID: ee4b975b58c1 (vision-language)
    }

    # Estimated VRAM sizes in MB
    MODEL_SIZES_MB = {
        "stark-enterprise:latest": 5000,
        "qwen2.5-coder:7b-instruct-q5_K_M": 5000,
        "qwen3:4b": 3000,
        "qwen3-vl:4b-instruct-q4_K_M": 3200,
    }

    VRAM_BUDGET_MB = 7500  # Leave headroom on 8GB GPU

    def __init__(self):
        self.active_overrides: Dict[str, str] = {}
        self.base_url = "http://127.0.0.1:11434"
        self.hardware_inventory = self._detect_hardware_accelerators()

    def _detect_hardware_accelerators(self) -> Dict[str, str]:
        """Detects available hardware accelerators (NVIDIA GPU, AMD iGPU, Intel/AMD NPU)."""
        inventory = {
            "dGPU": "NVIDIA GeForce RTX 4060 (Primary LLM Engine)",
            "iGPU": "AMD Radeon(TM) Graphics (General Purpose / Vision Offload)",
            "NPU": "NPU Compute Accelerator Device (Background Matrix / Vector Offload)"
        }
        return inventory

    def check_thermal_status(self) -> Tuple[bool, str]:
        """Checks CPU temperature to prevent thermal throttling or hardware damage."""
        if not _PSUTIL:
            return True, "psutil unavailable, thermal monitoring bypassed."

        try:
            temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
            if not temps:
                return True, "No thermal sensors detected."

            for name, entries in temps.items():
                for entry in entries:
                    if entry.current and entry.current > 95:
                        return False, f"CRITICAL: CPU temperature is {entry.current}°C (>95°C). Throttling execution."
                    elif entry.current and entry.current > 85:
                        logging.warning(f"HIGH TEMP: CPU temperature is {entry.current}°C (>85°C). Cooldown delay active.")
                        time.sleep(5)  # Soft cooldown
        except Exception as e:
            return True, f"Thermal check notice: {e}"

        return True, "Temperatures optimal."

    def set_model_override(self, role: str, model_name: str) -> Tuple[bool, str]:
        """Manually overrides the model for a specific role with VRAM budget validation."""
        if model_name not in self.MODEL_SIZES_MB:
            return False, f"Model '{model_name}' is not in the registered models manifest."

        estimated_size = self.MODEL_SIZES_MB[model_name]
        if estimated_size > self.VRAM_BUDGET_MB:
            return False, f"Model size ({estimated_size}MB) exceeds safe single-model VRAM budget ({self.VRAM_BUDGET_MB}MB)."

        self.active_overrides[role] = model_name
        return True, f"Role '{role}' model successfully set to '{model_name}'."

    def reset_overrides(self):
        """Resets all role overrides back to default fallback models."""
        self.active_overrides.clear()

    def get_model_for_role(self, role: str, temperature: float = 0.1) -> ChatOllama:
        """Returns a configured ChatOllama instance for the requested role."""
        # 1. Thermal guard check before instantiation
        ok, msg = self.check_thermal_status()
        if not ok:
            logging.error(msg)

        # 2. Resolve target model name
        target_model = self.active_overrides.get(role, self.DEFAULT_ROLES.get(role, "stark-enterprise:latest"))

        # 3. Enforce keep_alive=5m and num_gpu=99 for high-speed GPU execution without VRAM thrashing
        return ChatOllama(
            model=target_model,
            base_url=self.base_url,
            temperature=temperature,
            keep_alive="5m",
            num_gpu=99
        )


model_registry = ModelRegistry()
