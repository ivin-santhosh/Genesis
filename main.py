# -*- coding: utf-8 -*-

# For forcing installation of the essential packages first
# =========================================================
# CTO SYSTEM ENGINE: FACTORY DEPENDENCY REPAIR & LOADER
# =========================================================
import sys
import subprocess
import warnings

# Suppress the harmless but annoying urllib3 dependency warning
warnings.filterwarnings("ignore", category=UserWarning, module="requests")


def secure_system_bootstrap():
    """Bootstraps missing pip engine and automatically pulls framework layers."""
    active_python = sys.executable
    print(f"⚙️ Target Engine Path: {active_python}")
    
    # 1. Force bootstrap the 'pip' package installer engine if missing
    try:
        import pip
    except ImportError:
        print("🔧 Pip engine missing in Spyder 6 sandbox. Injecting native installer binary...")
        try:
            # Runs Python's built-in recovery framework package deployment tool
            subprocess.check_call([active_python, "-m", "ensurepip", "--default-pip"])
            print("✅ Pip engine deployed successfully into Spyder path.")
        except Exception as e:
            print(f"❌ Failed to run ensurepip tool: {str(e)}")
            return False

    # 2. Sequential dependency matrix extraction loop
    packages = [
        "langchain",
        "langchain-ollama", 
        "langchain-core", 
        "langgraph", 
        "duckduckgo-search",
        "langchain-mcp-adapters",
        "requests",
        "mcp<2",
        "urllib3",
        "pywin32"
    ]
    
    for pkg in packages:
        module_name = pkg.replace("-", "_")
        try:
            __import__(module_name)
        except ImportError:
            print(f"📦 Downloading and matching: {pkg}...")
            try:
                # Use absolute executable references to download cleanly
                subprocess.check_call([
                    active_python, "-m", "pip", "install", 
                    pkg, "--upgrade", "--no-warn-script-location"
                ])
                print(f"🔗 Linked dependency: {pkg}")
            except Exception as error:
                print(f"❌ Aborted installation on {pkg}: {str(error)}")
                return False
                
    print("🚀 All framework arrays mapped safely!")
    return True

# Initialize structural runtime validation gate
if not secure_system_bootstrap():
    print("⚠️ Architecture halt: Environment setup incomplete.")
    sys.exit(1)



# Main Program Begins

"""
Project Genesis - Main Desktop Interface Engine
Date: August 2026
Location: Kalyan, Maharashtra, India

The command center for Project Genesis. Integrates:
1. 0ms Spinal Reflex Arc (routing.py) - Bypasses LLMs for instant actions.
2. LangGraph Neural Pathways (graph.py) - Prefrontal, Muscle, and Immune Agents.
3. Nervous System Observer (logger.py) - Real-time biomimetic transparency.
4. Meta-Hand Motor Cortex (meta_hand.py) - MCP Tool Execution Registry.
"""

import sys
import os
import asyncio
from typing import List

# Ensure we can import from the Genesis package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Genesis.core.memory import GenesisState
from Genesis.core.routing import ReflexRouter
from Genesis.core.logger import observer
from Genesis.core.graph import process_stimulus
from Genesis.tools.meta_hand import meta_hand_manager

# Import MCP Client to connect to your existing mcp_tools.py
from langchain_mcp_adapters.client import MultiServerMCPClient

async def bootstrap_mcp_tools():
    """
    Connects to the local MCP server (mcp_tools.py) and loads capabilities into Meta-Hand.
    """
    observer.log_thought_process("Meta-Hand", "Bootstrapping Motor Cortex", "Connecting to local MCP server...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(current_dir, "tools", "mcp_tools.py")
    print("MCP SERVER PATH : " + str(server_path)+"\n")
    
    if not os.path.exists(server_path):
        observer.log_thought_process("System", "CRITICAL ERROR", f"Cannot find mcp_tools.py at {server_path}")
        sys.exit(1)

    client = MultiServerMCPClient(
        {
            "LocalBrain":  {
                "command": "python",
                "args": [server_path],
                "transport": "stdio",
            }
        }
    )
    print(f"Client:\n{'-'*50}\n{client}\n")
    # Handshake and discover tools
    tools = await client.get_tools()
    print(f"Tools:\n{'-'*50}\n{tools}\n")
    print(f"type(tools):\n{type(tools)}\n")
    
    # Register all discovered MCP tools into Meta-Hand's O(1) registry
    for t in tools:
        meta_hand_manager.register_tool(t.name, t)
        
    observer.log_thought_process("Meta-Hand", "Muscle Memory Updated", f"Successfully loaded {len(tools)} capabilities from MCP.")
    return client

async def initialize_ecosystem():
    """
    Boots up the autonomic nervous system and initializes the global state space.
    """
    print("\n" + "="*70)
    print("🟢 PROJECT GENESIS: BIOMIMETIC AI ECOSYSTEM OPERATIONAL")
    print(f"📍 Location: Kalyan, Maharashtra | Date: August 2026")
    print("="*70)
    
    # 1. Boot up MCP and load tools
    mcp_client = await bootstrap_mcp_tools()
    
    # 2. Instantiate Spinal Reflex Arc
    spinal_cord = ReflexRouter()
    
    # 3. Initialize Global State Space (Bloodstream)
    initial_state: GenesisState = {
        "messages": [],
        "next_node": "Nexus",
        "user_profit_metric": 100.0,
        "active_permissions": {"internet_access": "Yellow", "execute_code": "Red"},
        "task_dag": [],
        "meta_hand_cache": {} # Holds active tool pointers
    }
    
    observer.log_thought_process("System", "Ecosystem Bootstrapped", "VRAM limits, state space, and reflex pathways initialized.")
    return spinal_cord, initial_state, mcp_client

async def run_desktop_interface():
    """
    Interactive Desktop Command Shell for Project Genesis.
    """
    spinal_cord, current_state, mcp_client = await initialize_ecosystem()
    
    print("\n💡 Genesis Interface Ready. Type 'exit', 'quit', or 'stop' to shut down.\n")
    
    while True:
        try:
            # 1. Capture Stimulus
            user_input = input("👤 [Human Operator] >>> ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["exit", "quit", "stop"]:
                observer.log_thought_process("System", "Shutdown Sequence", "Powering down neural pathways cleanly.")
                print("\n🛑 Genesis ecosystem safely hibernating. Goodbye, sir.\n")
                break
            
            # 2. Check Spinal Reflex Arc (0ms Latency Bypass)
            reflex_response = spinal_cord.evaluate(user_input)
            
            if reflex_response:
                if reflex_response == "COMMAND_FLUSH_MEMORY":
                    current_state["messages"] = []
                    print("\n⚡ [Spinal Reflex] Memory state flushed completely. Context window reset.\n")
                else:
                    print(f"\n⚡ [Spinal Reflex Response] {reflex_response}\n")
                continue # Skip expensive LLM processing
            
            # 3. Append User Message to State
            from langchain_core.messages import HumanMessage
            current_state["messages"].append(HumanMessage(content=user_input))
            
            # 4. Route Stimulus through Neural Graph (Nexus -> Coder/Thinker)
            final_state = process_stimulus(user_input, current_state)
            
            # 5. Extract Final Verified Output
            if final_state.get("messages"):
                last_message = final_state["messages"][-1]
                print(f"\n🤖 [Genesis Organism Output]:\n{last_message.content}\n")
                
            # Update working state
            current_state = final_state
            
        except KeyboardInterrupt:
            print("\n\n🛑 Emergency Interruption Signal Received. Hibernating Genesis.")
            break
        except Exception as e:
            import traceback
            observer.log_thought_process("System", "Immune Defense Failure", f"Unhandled anomaly: {str(e)}")
            print(f"\n❌ System Fault: {traceback.format_exc()}\n")

if __name__ == "__main__":
    # Windows-specific async loop policy fix
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    asyncio.run(run_desktop_interface())