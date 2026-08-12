# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import asyncio
import warnings

# GPU-First: Flash attention for speed + single-request mode to prevent VRAM thrashing
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")
os.environ.setdefault("OLLAMA_NUM_PARALLEL", "1")

# =========================================================
# THE SPYDER IDE "FILENO" MASTER PATCH
# =========================================================
_orig_popen = subprocess.Popen
_devnull_out = open(os.devnull, 'w')
_devnull_in = open(os.devnull, 'r')

class SpyderSafePopen(_orig_popen):
    def __init__(self, *args, **kwargs):
        def is_fake_stream(obj):
            if obj is None or isinstance(obj, int):
                return False
            try:
                obj.fileno()
                return False
            except Exception:
                return True

        if is_fake_stream(kwargs.get('stderr')):
            kwargs['stderr'] = _devnull_out
        if is_fake_stream(kwargs.get('stdout')):
            kwargs['stdout'] = _devnull_out
        if is_fake_stream(kwargs.get('stdin')):
            kwargs['stdin'] = _devnull_in

        super().__init__(*args, **kwargs)

subprocess.Popen = SpyderSafePopen

# =========================================================
# CTO SYSTEM ENGINE: FACTORY DEPENDENCY REPAIR & LOADER
# =========================================================
warnings.filterwarnings("ignore", category=UserWarning, module="requests")

def secure_system_bootstrap():
    """Bootstraps missing pip engine and automatically pulls framework layers."""
    import site
    import importlib

    active_python = sys.executable
    print(f"⚙️ Target Engine Path: {active_python}")

    try:
        import pip
    except ImportError:
        print("🔧 Pip engine missing. Injecting native installer binary...")
        try:
            subprocess.check_call([active_python, "-m", "ensurepip", "--default-pip"])
            print("✅ Pip engine deployed successfully.")
        except Exception as e:
            print(f"❌ Failed to run ensurepip tool: {str(e)}")
            return False

    packages = [
        "langchain", "langchain-ollama", "langchain-core", 
        "langgraph", "duckduckgo-search", "langchain-mcp-adapters",
        "requests", "mcp<2", "urllib3", "pywin32", "nest-asyncio", "rich",
        "python-telegram-bot", "telegramify-markdown", "wakeonlan"
    ]

    for pkg in packages:
        module_name = pkg.replace("-", "_").split("[")[0]
        try:
            __import__(module_name)
        except ImportError:
            print(f"📦 Downloading and matching: {pkg}...")
            try:
                subprocess.check_call([
                    active_python, "-m", "pip", "install", 
                    pkg, "--upgrade", "--no-warn-script-location"
                ])
                print(f"🔗 Linked dependency: {pkg}")
            except Exception as error:
                print(f"❌ Aborted installation on {pkg}: {str(error)}")
                return False

    importlib.invalidate_caches()
    user_site = site.getusersitepackages()
    if user_site not in sys.path:
        sys.path.append(user_site)

    print("🚀 All framework arrays mapped safely!")
    return True

if not secure_system_bootstrap():
    print("⚠️ Architecture halt: Environment setup incomplete.")
    sys.exit(1)


# =========================================================
# MAIN PROGRAM BEGINS
# =========================================================
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Genesis.core.memory import GenesisState
from Genesis.core.routing import ReflexRouter
from Genesis.core.logger import observer
from Genesis.core.graph import process_stimulus, set_mcp_client
from Genesis.tools.meta_hand import meta_hand_manager
from Genesis.core.renderer import render_ai_response, render_banner
from Genesis.interfaces.remote_manager import configure_power_settings
from langchain_mcp_adapters.client import MultiServerMCPClient

async def bootstrap_mcp_tools():
    observer.log_thought_process("Meta-Hand", "Bootstrapping Motor Cortex", "Connecting to local MCP server...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(current_dir, "tools", "mcp_tools.py")

    if not os.path.exists(server_path):
        observer.log_thought_process("System", "CRITICAL ERROR", f"Cannot find mcp_tools.py at {server_path}")
        sys.exit(1)

    venv_python = os.path.join(current_dir, ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        observer.log_thought_process("System", "WARNING", f".venv not found at {venv_python}. Falling back to sys.executable.")
        venv_python = sys.executable

    observer.log_thought_process("Meta-Hand", "MCP Engine", f"Child process target: {venv_python}")

    client = MultiServerMCPClient(
        {
            "LocalBrain": {
                "command": venv_python,
                "args": [server_path],
                "transport": "stdio",
            }
        }
    )

    _real_stderr = sys.stderr
    sys.stderr = _devnull_out
    try:
        tools = await client.get_tools()
    finally:
        sys.stderr = _real_stderr

    for t in tools:
        meta_hand_manager.register_tool(t.name, t)

    observer.log_thought_process("Meta-Hand", "Muscle Memory Updated", f"Successfully loaded {len(tools)} capabilities from MCP.")
    return client


def ensure_ollama_running() -> bool:
    import urllib.request
    import urllib.error
    import time

    HEALTH_URL = "http://localhost:11434/api/tags"

    CANDIDATE_PATHS = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Ollama", "ollama.exe"),
        os.path.join("C:\\", "Program Files", "Ollama", "ollama.exe"),
        "ollama",
    ]

    def is_alive() -> bool:
        try:
            urllib.request.urlopen(HEALTH_URL, timeout=2)
            return True
        except Exception:
            return False

    if is_alive():
        print("✅ [Ollama] Engine is live and responsive.")
        return True

    print("⚡ [Ollama] Not detected. Searching for executable...")

    ollama_exe = None
    for path in CANDIDATE_PATHS:
        if path == "ollama":
            try:
                result = subprocess.run(["ollama", "--version"], capture_output=True, timeout=3)
                if result.returncode == 0:
                    ollama_exe = "ollama"
                    break
            except Exception:
                continue
        elif os.path.exists(path):
            ollama_exe = path
            break

    if not ollama_exe:
        print("❌ [Ollama] Executable not found. Install from https://ollama.com")
        return False

    print(f"🔍 [Ollama] Found at: {ollama_exe}")
    print("🚀 [Ollama] Launching background engine... (this may take up to 30s)")

    subprocess.Popen(
        [ollama_exe, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    )

    TIMEOUT = 30
    for i in range(TIMEOUT):
        time.sleep(1)
        if is_alive():
            print(f"✅ [Ollama] Engine live after {i + 1}s.")
            return True
        dots = "." * ((i % 3) + 1)
        print(f"   ⏳ Warming up{dots} ({i + 1}/{TIMEOUT}s)", end="\r")

    print(f"\n❌ [Ollama] Did not respond within {TIMEOUT} seconds.")
    return False


async def initialize_ecosystem():
    render_banner("🟢 PROJECT GENESIS: BIOMIMETIC AI ECOSYSTEM OPERATIONAL\n📍 Location: Kalyan, Maharashtra | Date: August 2026")

    # Power Management Configuration
    ok_pwr, msg_pwr = configure_power_settings()
    if ok_pwr:
        print(f"⚡ [PowerConfig] {msg_pwr}")

    if not ensure_ollama_running():
        print("⚠️  Ollama is required for LLM queries. Proceeding without guarantee.")

    mcp_client = await bootstrap_mcp_tools()
    set_mcp_client(mcp_client)
    spinal_cord = ReflexRouter()

    initial_state: GenesisState = {
        "messages": [],
        "next_node": "Nexus",
        "user_profit_metric": 100.0,
        "active_permissions": {"internet_access": "Yellow", "execute_code": "Red"},
        "task_dag": [],
        "meta_hand_cache": {},
        "agent_messages": [],
        "autonomous_iteration_count": 0
    }

    observer.log_thought_process("System", "Ecosystem Bootstrapped", "VRAM limits, state space, and reflex pathways initialized.")
    return spinal_cord, initial_state, mcp_client


async def run_desktop_interface():
    spinal_cord, current_state, mcp_client = await initialize_ecosystem()

    while True:
        print("\n💡 Genesis Interface Ready. Type 'exit', 'quit', or 'stop' to shut down.\n")
        try:
            user_input = input("👤 [Human Operator] >>> ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "stop"]:
                observer.log_thought_process("System", "Shutdown Sequence", "Powering down neural pathways cleanly.")
                print("\n🛑 Genesis ecosystem safely hibernating. Goodbye, sir.\n")
                break

            reflex_response = spinal_cord.evaluate(user_input)
            if reflex_response:
                if reflex_response == "COMMAND_FLUSH_MEMORY":
                    current_state["messages"] = []
                    print("\n⚡ [Spinal Reflex] Memory state flushed completely. Context window reset.\n")
                else:
                    print(f"\n⚡ [Spinal Reflex Response] {reflex_response}\n")
                continue

            from langchain_core.messages import HumanMessage
            current_state["messages"].append(HumanMessage(content=user_input))

            final_state = process_stimulus(user_input, current_state)

            if final_state.get("messages"):
                last_message = final_state["messages"][-1]
                render_ai_response(last_message.content)

            current_state = final_state

        except KeyboardInterrupt:
            print("\n\n🛑 Emergency Interruption Signal Received. Hibernating Genesis.")
            break
        except Exception as e:
            import traceback
            observer.log_thought_process("System", "Immune Defense Failure", f"Unhandled anomaly: {str(e)}")
            print(f"\n❌ System Fault: {traceback.format_exc()}\n")


if __name__ == "__main__":
    if sys.platform == 'win32':
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

    import nest_asyncio
    nest_asyncio.apply()

    if "--telegram" in sys.argv:
        print("🚀 Starting Genesis SentinelAI Telegram Interface...")
        from Genesis.interfaces.telegram_bot import create_bot_application
        app = create_bot_application()
        app.run_polling()
    else:
        asyncio.run(run_desktop_interface())