# -*- coding: utf-8 -*-
"""
Project Genesis - Multi-Mode Output Renderer (V2.0)
Supports 4 modes: SPYDER, TERMINAL, TELEGRAM, PLAIN.
Provides callback dispatch, Telegram HTML formatting, expandable thinking blocks, and intelligent message splitting.
"""

import html
import os
import re
import sys
from typing import Callable, Optional, Dict, Any, List

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    from rich.theme import Theme

    _theme = Theme({
        "g.head": "bold cyan",
        "g.ok": "bold green",
        "g.warn": "bold yellow",
        "g.err": "bold red",
    })
    _con = Console(theme=_theme, force_terminal=True, width=100)
    _RICH = True
except ImportError:
    _RICH = False
    _con = None


# --- MODE AUTO-DETLECTION & CONFIG ---
def _detect_initial_mode() -> str:
    """Detects default environment mode on startup."""
    if "spyder" in sys.modules or hasattr(sys.stderr, "kernel"):
        return "SPYDER"
    elif hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        return "TERMINAL"
    return "PLAIN"


_CURRENT_MODE = _detect_initial_mode()
_OUTPUT_CALLBACK: Optional[Callable[[str, str, Dict[str, Any]], None]] = None


def set_output_mode(mode: str):
    """Sets renderer mode: 'SPYDER', 'TERMINAL', 'TELEGRAM', or 'PLAIN'."""
    global _CURRENT_MODE
    valid_modes = ["SPYDER", "TERMINAL", "TELEGRAM", "PLAIN"]
    mode_upper = mode.upper()
    if mode_upper in valid_modes:
        _CURRENT_MODE = mode_upper
    else:
        _CURRENT_MODE = "PLAIN"


def get_output_mode() -> str:
    """Returns current active output mode."""
    return _CURRENT_MODE


def set_output_callback(callback: Optional[Callable[[str, str, Dict[str, Any]], None]]):
    """
    Registers a custom callback for output dispatch (used by Telegram Bot interface).
    Callback signature: fn(event_type: str, content: str, metadata: dict)
    event_type: 'ai_response' | 'system_event' | 'banner' | 'agent_thinking' | 'swarm_message'
    """
    global _OUTPUT_CALLBACK
    _OUTPUT_CALLBACK = callback


# --- TELEGRAM FORMATTING HELPERS ---
def to_telegram_html(text: str) -> str:
    """
    Converts standard Markdown into valid, clean Telegram HTML.
    Preserves code blocks, bold, italic, inline code, and wraps thinking in <blockquote expandable>.
    """
    if not text:
        return ""

    # 1. Protect code blocks (```code```)
    code_blocks = []
    def save_code_block(match):
        lang = match.group(1) or ""
        code_content = html.escape(match.group(2))
        placeholder = f"___CODE_BLOCK_{len(code_blocks)}___"
        if lang:
            code_blocks.append(f'<pre><code class="language-{lang}">{code_content}</code></pre>')
        else:
            code_blocks.append(f'<pre><code>{code_content}</code></pre>')
        return placeholder

    text = re.sub(r'```(\w+)?\n(.*?)```', save_code_block, text, flags=re.DOTALL)

    # 2. Protect inline code (`code`)
    inline_codes = []
    def save_inline_code(match):
        code_content = html.escape(match.group(1))
        placeholder = f"___INLINE_CODE_{len(inline_codes)}___"
        inline_codes.append(f'<code>{code_content}</code>')
        return placeholder

    text = re.sub(r'`([^`]+)`', save_inline_code, text)

    # 3. HTML escape remaining plain text
    text = html.escape(text)

    # 4. Convert basic markdown formatting to HTML
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # Bold
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)      # Italic
    text = re.sub(r'__(.*?)__', r'<u>\1</u>', text)      # Underline
    text = re.sub(r'~(.*?)~', r'<s>\1</s>', text)        # Strikethrough

    # 5. Restore inline codes and code blocks
    for i, code_html in enumerate(inline_codes):
        text = text.replace(f"___INLINE_CODE_{i}___", code_html)

    for i, block_html in enumerate(code_blocks):
        text = text.replace(f"___CODE_BLOCK_{i}___", block_html)

    return text


def format_expandable_thinking(agent_name: str, action: str, full_thinking: str) -> str:
    """Formats intermediate thinking steps into Telegram Bot API 10.2 expandable blockquotes."""
    summary_line = f"🧠 <b>{html.escape(agent_name)}</b>: {html.escape(action)}"
    escaped_body = html.escape(full_thinking)
    return f"{summary_line}\n<blockquote expandable>{escaped_body}</blockquote>"


def split_telegram_message(content: str, max_length: int = 3800) -> List[str]:
    """
    Splits long messages at paragraph boundaries without breaking code blocks mid-block.
    Adds clear continuation headers when split.
    """
    if len(content) <= max_length:
        return [content]

    chunks = []
    lines = content.split("\n")
    current_chunk = []
    current_len = 0
    in_code_block = False
    current_lang = ""

    for line in lines:
        code_match = re.match(r'^\s*```(\w+)?', line)
        if code_match:
            if not in_code_block:
                in_code_block = True
                current_lang = code_match.group(1) or ""
            else:
                in_code_block = False
                current_lang = ""

        line_len = len(line) + 1
        if current_len + line_len > max_length:
            # Need to split
            if in_code_block:
                # Close code block in current chunk and re-open in next chunk
                current_chunk.append("```")
                current_chunk.append("⬇️ <i>[Code continues in next message...]</i>")
                chunks.append("\n".join(current_chunk))

                current_chunk = [f"📄 <i>[Continued code snippet]</i>", f"```{current_lang}", line]
                current_len = sum(len(l) + 1 for l in current_chunk)
            else:
                current_chunk.append("⬇️ <i>[Continued in next message...]</i>")
                chunks.append("\n".join(current_chunk))

                current_chunk = ["📄 <i>[Continued response]</i>", line]
                current_len = sum(len(l) + 1 for l in current_chunk)
        else:
            current_chunk.append(line)
            current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


# --- MAIN RENDER FUNCTIONS ---
def render_ai_response(content: str, agent_label: str = "Genesis Organism"):
    """Renders main AI response according to active mode or callback."""
    if _OUTPUT_CALLBACK is not None:
        _OUTPUT_CALLBACK("ai_response", content, {"agent_label": agent_label, "mode": _CURRENT_MODE})
        return

    if _CURRENT_MODE in ["SPYDER", "TERMINAL"] and _RICH:
        md = Markdown(content)
        _con.print()
        _con.print(Panel(md,
            title=f"🤖 [bold cyan]{agent_label}[/bold cyan]",
            subtitle="[dim]Genesis Ecosystem[/dim]",
            border_style="cyan", padding=(1, 2)))
        _con.print()
    else:
        print(f"\n{'─'*70}\n🤖 [{agent_label}]:\n{content}\n{'─'*70}\n", flush=True)
    sys.stdout.flush()


def render_system_event(icon: str, action: str, rationale: str):
    """Renders system/agent events according to active mode or callback."""
    if _OUTPUT_CALLBACK is not None:
        _OUTPUT_CALLBACK("system_event", f"{icon} Action: {action}\n   ↳ Rationale: {rationale}", {
            "icon": icon, "action": action, "rationale": rationale, "mode": _CURRENT_MODE
        })
        return

    if _CURRENT_MODE in ["SPYDER", "TERMINAL"] and _RICH:
        _con.print(f"\n{icon} Action: [bold]{action}[/bold]")
        _con.print(f"   ↳ {rationale}", style="dim")
    else:
        print(f"\n{icon} Action: {action}", flush=True)
        print(f"   ↳ {rationale}", flush=True)
    sys.stdout.flush()


def render_banner(text: str):
    """Renders prominent startup banner."""
    if _OUTPUT_CALLBACK is not None:
        _OUTPUT_CALLBACK("banner", text, {"mode": _CURRENT_MODE})
        return

    if _CURRENT_MODE in ["SPYDER", "TERMINAL"] and _RICH:
        _con.print()
        _con.print(Panel(Text(text, justify="center"),
                          border_style="bold green", padding=(1, 2)))
        _con.print()
    else:
        print(f"\n{'═'*70}\n{text}\n{'═'*70}", flush=True)
    sys.stdout.flush()
