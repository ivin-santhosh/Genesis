# -*- coding: utf-8 -*-
"""
Project Genesis - The Connective Tissue (StateGraph)
Wires all organs together into a cohesive, synchronous biological ecosystem.
"""

from langgraph.graph import StateGraph, START, END
from Genesis.core.memory import GenesisState, ContextCompressor
from Genesis.core.logger import observer
from Genesis.agents.nexus import nexus_node
from Genesis.agents.coder import coder_node
from Genesis.agents.thinker import thinker_node

# Initialize the biological components
lungs = ContextCompressor()
workflow = StateGraph(GenesisState)

workflow.add_node("Nexus", nexus_node)
workflow.add_node("Coder", coder_node)
workflow.add_node("Thinker", thinker_node)

# Stimulus enters the Brain
workflow.add_edge(START, "Nexus")

# The Brain routes the signal
workflow.add_conditional_edges(
    "Nexus",
    lambda state: state["next_node"],
    {
        "Coder": "Coder",
        "Thinker": "Thinker",
        "END": END
    }
)

# Muscles always report back to the Immune System for safety verification
workflow.add_edge("Coder", "Thinker")

# Immune System finalizes the thought process and outputs to the Human
workflow.add_edge("Thinker", END)

# Compile the living ecosystem
ecosystem = workflow.compile()

def process_stimulus(user_input: str, current_state: GenesisState) -> GenesisState:
    """
    The main execution loop for external interactions.
    Compresses memory (Lungs), tracks state (Nervous System), and invokes the graph.
    """
    # 1. The Lungs breathe out stale tokens if we exceed VRAM limits
    current_state["messages"] = lungs.compress(current_state["messages"])
    
    # 2. Stimulus is sent through the ecosystem
    print("\n" + "="*50)
    observer.log_thought_process("System", "Stimulus Received", "Sending prompt through neural pathways...")
    
    # 3. Graph Execution
    final_state = ecosystem.invoke(current_state)
    
    # 4. Save the memory trace for backpropagation capabilities
    observer.save_state_trace(final_state, "END_OF_CYCLE")
    
    print("="*50 + "\n")
    return final_state