# -*- coding: utf-8 -*-
"""
Project Genesis - Terminal Renderer (V1.0)
Converts AI markdown output to beautiful ANSI-styled terminal output.
Uses `rich` for professional rendering in Spyder's IPython console.
Falls back to plain text if `rich` is unavailable.
"""

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


def render_ai_response(content: str, agent_label: str = "Genesis Organism"):
    """Renders AI response in a styled rich panel with markdown formatting."""
    if not _RICH:
        print(f"\n{'─'*70}\n🤖 [{agent_label}]:\n{content}\n{'─'*70}\n")
        return
    md = Markdown(content)
    _con.print()
    _con.print(Panel(md,
        title=f"🤖 [bold cyan]{agent_label}[/bold cyan]",
        subtitle="[dim]Genesis Ecosystem[/dim]",
        border_style="cyan", padding=(1, 2)))
    _con.print()


def render_system_event(icon: str, action: str, rationale: str):
    """Renders system/agent events with styled output."""
    if not _RICH:
        print(f"\n{icon} Action: {action}")
        print(f"   ↳ Rationale: {rationale}")
        return
    _con.print(f"\n{icon} Action: [bold]{action}[/bold]")
    _con.print(f"   ↳ {rationale}", style="dim")


def render_banner(text: str):
    """Renders a prominent startup banner."""
    if not _RICH:
        print(f"\n{'═'*70}\n{text}\n{'═'*70}")
        return
    _con.print()
    _con.print(Panel(Text(text, justify="center"),
                      border_style="bold green", padding=(1, 2)))
    _con.print()
