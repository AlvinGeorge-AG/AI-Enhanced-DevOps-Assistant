# Centralized log formatter for SentinelAI.
#
# Every piece of terminal output in the system flows through this module.
# Each function maps to a specific semantic log level with a distinct
# visual style, so anyone reading `docker compose logs -f sentinel_api`
# can instantly tell what kind of event they're looking at.
#
# Color scheme:
#   dim gray    = routine / informational (most lines — should visually recede)
#   bold green  = system healthy / approved
#   bold cyan   = active infrastructure mutation in progress
#   yellow      = safety guardrail rejection (informational, not alarming)
#   white on red = Rule 0 / emergency override (unmistakable alarm)

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Display thresholds for color-coding metrics. These mirror the values in
# brain/safety_engine.py but are defined here independently to avoid a
# circular import (safety_engine.py imports log_emergency_override from us).
# These are ONLY used for visual styling — actual decision logic lives in
# safety_engine.py and is the single source of truth.
HIGH_CPU_THRESHOLD = 70.0
LOW_CPU_THRESHOLD = 20.0
HIGH_ERROR_RATE_THRESHOLD = 5.0
HIGH_MEMORY_THRESHOLD = 150.0


console = Console(force_terminal=True, color_system="standard")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metric_style(metric: str, value: float) -> str:
    """Return a rich style string based on how healthy a metric value is."""
    thresholds = {
        "cpu_usage_percent": (HIGH_CPU_THRESHOLD, LOW_CPU_THRESHOLD),
        "memory_usage_mb": (HIGH_MEMORY_THRESHOLD, HIGH_MEMORY_THRESHOLD * 0.7),
        "error_rate_percent": (HIGH_ERROR_RATE_THRESHOLD, HIGH_ERROR_RATE_THRESHOLD * 0.5),
        "active_replicas": None,
        "request_rate_per_sec": None,
        "active_alerts": None,
    }
    bounds = thresholds.get(metric)
    if bounds is None:
        return "white"

    critical, warning = bounds
    # For active_replicas, lower is worse — but it's handled above as None.
    if value >= critical:
        return "bold red"
    elif value >= warning:
        return "yellow"
    return "green"


def _status_dot(metric: str, value: float) -> str:
    """Return a colored status indicator label."""
    thresholds = {
        "cpu_usage_percent": (HIGH_CPU_THRESHOLD, LOW_CPU_THRESHOLD),
        "memory_usage_mb": (HIGH_MEMORY_THRESHOLD, HIGH_MEMORY_THRESHOLD * 0.7),
        "error_rate_percent": (HIGH_ERROR_RATE_THRESHOLD, HIGH_ERROR_RATE_THRESHOLD * 0.5),
    }
    bounds = thresholds.get(metric)
    if bounds is None:
        return ""

    critical, warning = bounds
    if value >= critical:
        return "[bold red]CRITICAL[/bold red]"
    elif value >= warning:
        return "[yellow]ELEVATED[/yellow]"
    return "[green]HEALTHY[/green]"


# ---------------------------------------------------------------------------
# Public API — 7 semantic logging functions + 1 utility
# ---------------------------------------------------------------------------

def log_info(message: str, style: str = "dim") -> None:
    """General-purpose informational line. Defaults to dim so it doesn't
    compete with more important output."""
    console.print(f"  {message}", style=style)


def log_system_state(state: dict, title: str = "SYSTEM STATE") -> None:
    """Render cpu/memory/error_rate/request_rate/active_replicas as a
    color-coded table. Single source of truth for what this looks like —
    used by both CRON checks and webhook handlers."""

    table = Table(
        title=f"  {title}",
        title_style="bold white",
        border_style="cyan",
        show_header=True,
        header_style="bold cyan",
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Metric", style="white", min_width=22)
    table.add_column("Value", justify="right", min_width=10)
    table.add_column("Status", justify="center", min_width=10)

    # Only display numeric metrics in the table. Non-numeric fields like
    # recent_history (list of dicts) are excluded — they're not metrics and
    # would render as unreadable raw blobs.
    SKIP_KEYS = {"recent_history", "alert_context", "user_chat_message"}

    for metric, value in state.items():
        if metric in SKIP_KEYS:
            continue
        if isinstance(value, (int, float)):
            formatted = f"{value:.2f}"
            style = _metric_style(metric, value)
            status = _status_dot(metric, value)
        else:
            formatted = str(value) if value is not None else "N/A"
            style = "dim"
            status = ""

        table.add_row(metric, f"[{style}]{formatted}[/{style}]", status)

    console.print()
    console.print(table)
    console.print()

    # Print recent history below the table instead of dumping raw JSON
    history = state.get("recent_history")
    if history and isinstance(history, list):
        console.print("  [bold white]Recent Infrastructure History:[/bold white]\n")
        for item in history:
            time = item.get("time", "")
            action = item.get("action", "")
            status = item.get("status", "")
            reason = item.get("reason", "")
            
            # Highlight executed actions differently from skipped ones
            status_color = "bold green" if status == "executed" else "dim"
            action_color = "bold cyan" if action != "no_action" else "dim"
            
            console.print(f"    [white]•[/white] [{time}] [{action_color}]{action}[/{action_color}] ([{status_color}]{status}[/{status_color}])")
            console.print(f"      [dim]↳ {reason}[/dim]\n")


def log_decision(decision: dict, source: str) -> None:
    """Render an LLM or safety-engine decision (action/reason/confidence).
    Confidence is color-coded; action is bolded; reason is word-wrapped."""

    action = decision.get("action", "unknown")
    confidence = decision.get("confidence", 0.0)
    reason = decision.get("reason", "No reason provided.")

    # Color-code confidence: green >= 0.8, yellow 0.6-0.8, red < 0.6
    if isinstance(confidence, (int, float)):
        if confidence >= 0.8:
            conf_style = "bold green"
        elif confidence >= 0.6:
            conf_style = "bold yellow"
        else:
            conf_style = "bold red"
        conf_display = f"{confidence:.2f}"
    else:
        conf_style = "white"
        conf_display = str(confidence)

    # Action color: no_action = dim, mutations = cyan
    if action == "no_action":
        action_style = "dim"
    else:
        action_style = "bold cyan"

    content = Text()
    content.append(f"  [{source}] ", style="dim")
    content.append("LLM Decision\n", style="bold white")
    content.append(f"  Action:     ", style="dim")
    content.append(f"{action}\n", style=action_style)
    content.append(f"  Confidence: ", style="dim")
    content.append(f"{conf_display}\n", style=conf_style)
    content.append(f"  Reason:     ", style="dim")
    content.append(f"{reason}", style="white")

    console.print(content)
    console.print()


def log_routine_stable(reason: str) -> None:
    """Dim/gray styled — for the common 'no action needed' case.
    This is the overwhelming majority of log lines and should
    visually recede so it doesn't compete for attention."""
    console.print(f"  No action needed. {reason}", style="dim")
    console.print()


def log_action_executed(action: str, detail: str = "") -> None:
    """Bold cyan — an actual infrastructure mutation is happening.
    (scale_up / scale_down / restart_container via approved path.)"""
    content = Text()
    content.append("  ACTION EXECUTED: ", style="bold cyan")
    content.append(f"{action}\n", style="bold white")
    if detail:
        content.append(f"  Reason: {detail}", style="cyan")
    console.print(content)
    console.print()


def log_safety_rejection(reason: str) -> None:
    """Yellow styled panel — safety_engine rejected a decision
    (cooldown active, sustained-breach not met, confidence too low, etc).
    Not an emergency, just informational that a guardrail did its job."""
    panel = Panel(
        f"[yellow]{reason}[/yellow]",
        title="[bold yellow]SAFETY REJECTION[/bold yellow]",
        border_style="yellow",
        padding=(0, 1),
        expand=False,
    )
    console.print(panel)
    console.print()


def log_emergency_override(reason: str) -> None:
    """Bold white-on-red panel, unmistakable visual alarm. Reserved
    exclusively for Rule 0 (total fleet extinction) and memory leak
    hard override. This should look categorically different from
    every other log type — something has gone seriously wrong."""
    panel = Panel(
        f"[bold white]{reason}[/bold white]",
        title="[bold white on red] EMERGENCY OVERRIDE [/bold white on red]",
        border_style="bold red",
        padding=(1, 2),
        expand=False,
    )
    console.print()
    console.print(panel)
    console.print()


def log_alert_received(source: str) -> None:
    """Bold yellow panel header — marks the start of a webhook-triggered
    alert-handling block, replacing the '='*50 separator + emoji line."""
    panel = Panel(
        f"[bold white]Incoming alert from [bold yellow]{source}[/bold yellow][/bold white]",
        title="[bold yellow]ALERT RECEIVED[/bold yellow]",
        border_style="bold yellow",
        padding=(0, 1),
        expand=False,
    )
    console.print()
    console.print(panel)
