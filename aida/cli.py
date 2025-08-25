"""CLI interface for AIDA using Typer"""

import json
import sys
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .models import PlanRequest, Block
from .planner import plan_day
from .timer import run_timer
from .ics import export_to_ics
from .storage import load_preferences, save_session_log

app = typer.Typer(name="aida", help="🍅 AIDA - Adaptive Intelligent Day Assistant")
console = Console()


def load_plan_request(file_path: Path) -> PlanRequest:
    """Load plan request from JSON file"""
    if not file_path.exists():
        rprint(f"❌ File not found: {file_path}")
        raise typer.Exit(1)
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return PlanRequest.model_validate(data)
    except Exception as e:
        rprint(f"❌ Error loading plan: {e}")
        raise typer.Exit(1)


def display_plan(blocks: List[Block], summary: dict):
    """Display plan in a nice table format"""
    table = Table(title="📅 Your Day Plan")
    table.add_column("Time", style="cyan", no_wrap=True)
    table.add_column("Duration", justify="center")
    table.add_column("Type", style="magenta")
    table.add_column("Activity", style="green")
    
    for block in blocks:
        start_time = block.start.strftime("%H:%M")
        end_time = block.end.strftime("%H:%M")
        time_range = f"{start_time} - {end_time}"
        
        duration = f"{block.duration_minutes}m"
        
        # Add emoji based on block type
        emoji_map = {
            'pomodoro': '🍅',
            'break': '☕',
            'long_break': '🌟',
            'event': '📅'
        }
        type_display = f"{emoji_map.get(block.type, '⏰')} {block.type}"
        
        table.add_row(time_range, duration, type_display, block.title)
    
    console.print(table)
    
    # Display summary
    summary_text = f"""
📊 **Plan Summary**
• Total Pomodoros: {summary.total_pomodoros}
• Break Time: {summary.total_break_time} minutes
• Scheduled Tasks: {summary.scheduled_tasks}
• Free Time: {summary.free_time_minutes} minutes
"""
    
    if summary.unscheduled_tasks:
        summary_text += f"• Unscheduled: {', '.join(summary.unscheduled_tasks)}\n"
    
    if summary.deep_work_windows:
        summary_text += f"• Deep Work: {', '.join(summary.deep_work_windows)}\n"
    
    console.print(Panel(summary_text, title="Summary", border_style="blue"))


@app.command()
def plan(
    plan_file: Path = typer.Argument(..., help="JSON file with plan request"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save plan to JSON file"),
    ics: Optional[Path] = typer.Option(None, "--ics", help="Export to ICS file"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output")
):
    """📋 Generate a day plan from tasks and events"""
    
    # Load and process plan
    request = load_plan_request(plan_file)
    response = plan_day(request)
    
    if not quiet:
        display_plan(response.blocks, response.summary)
    
    # Save output if requested
    if output:
        with open(output, 'w') as f:
            json.dump(response.model_dump(), f, indent=2, default=str)
        rprint(f"💾 Plan saved to {output}")
    
    # Export to ICS if requested
    if ics:
        export_to_ics(response.blocks, ics)
        rprint(f"📅 Calendar exported to {ics}")


@app.command()
def run(
    plan_file: Path = typer.Argument(..., help="JSON file with plan request"),
    start_index: int = typer.Option(0, "--start", "-s", help="Start from block index"),
    tts: bool = typer.Option(False, "--tts", help="Enable text-to-speech"),
    save_log: bool = typer.Option(True, "--save/--no-save", help="Save session log")
):
    """🏃 Generate plan and run timer"""
    
    # Load and process plan
    request = load_plan_request(plan_file)
    response = plan_day(request)
    
    rprint("📋 Plan generated successfully!")
    display_plan(response.blocks, response.summary)
    
    # Confirm before starting timer
    if not typer.confirm("\n▶️  Start the timer?"):
        rprint("👋 See you later!")
        return
    
    # Run timer
    timer_state = run_timer(response.blocks, start_index, tts)
    
    # Save session log if requested
    if save_log:
        try:
            save_session_log(response.blocks, timer_state.completed_blocks, response.summary)
            rprint("💾 Session log saved")
        except Exception as e:
            rprint(f"⚠️  Warning: Could not save session log: {e}")


@app.command()
def timer(
    plan_file: Path = typer.Argument(..., help="JSON file with generated plan"),
    start_index: int = typer.Option(0, "--start", "-s", help="Start from block index"),
    tts: bool = typer.Option(False, "--tts", help="Enable text-to-speech")
):
    """⏰ Run timer on existing plan"""
    
    # Load plan from file
    if not plan_file.exists():
        rprint(f"❌ Plan file not found: {plan_file}")
        raise typer.Exit(1)
    
    try:
        with open(plan_file, 'r') as f:
            plan_data = json.load(f)
        
        # Handle both PlanResponse and plain blocks array
        if 'blocks' in plan_data:
            blocks_data = plan_data['blocks']
        else:
            blocks_data = plan_data
        
        blocks = [Block.model_validate(block) for block in blocks_data]
        
    except Exception as e:
        rprint(f"❌ Error loading plan: {e}")
        raise typer.Exit(1)
    
    if not blocks:
        rprint("❌ No blocks found in plan file!")
        raise typer.Exit(1)
    
    rprint(f"⏰ Starting timer with {len(blocks)} blocks")
    if start_index > 0:
        rprint(f"📍 Starting from block {start_index + 1}")
    
    run_timer(blocks, start_index, tts)


@app.command()
def status():
    """📊 Show current timer status"""
    rprint("📊 Timer status functionality not yet implemented")
    rprint("💡 Use 'aida run' or 'aida timer' to start a session")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current preferences"),
    workday_start: Optional[str] = typer.Option(None, help="Set workday start (HH:MM)"),
    workday_end: Optional[str] = typer.Option(None, help="Set workday end (HH:MM)"),
    pomodoro_min: Optional[int] = typer.Option(None, help="Set pomodoro duration"),
):
    """⚙️  Manage AIDA configuration"""
    
    if show:
        try:
            prefs = load_preferences()
            table = Table(title="🔧 AIDA Configuration")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Workday Start", prefs.workday_start.strftime("%H:%M %Z"))
            table.add_row("Workday End", prefs.workday_end.strftime("%H:%M %Z"))
            table.add_row("Pomodoro Duration", f"{prefs.pomodoro_min} min")
            table.add_row("Break Duration", f"{prefs.break_min} min")
            table.add_row("Long Break Duration", f"{prefs.long_break_min} min")
            table.add_row("Cycles per Long Break", str(prefs.cycles_per_long_break))
            
            console.print(table)
            
        except Exception as e:
            rprint(f"❌ Error loading preferences: {e}")
            raise typer.Exit(1)
    else:
        rprint("🔧 Configuration management not fully implemented yet")
        rprint("💡 Edit examples/today.json to customize preferences for now")


@app.command()
def version():
    """📋 Show AIDA version"""
    from . import __version__
    rprint(f"🍅 AIDA v{__version__}")


if __name__ == "__main__":
    app()