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
from .assistant import start_jarvis_assistant

app = typer.Typer(name="aida", help="AIDA - Adaptive Intelligent Day Assistant")
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
    table = Table(title="Your Day Plan")
    table.add_column("Time", style="cyan", no_wrap=True)
    table.add_column("Duration", justify="center")
    table.add_column("Type", style="magenta")
    table.add_column("Activity", style="green")
    
    for block in blocks:
        start_time = block.start.strftime("%H:%M")
        end_time = block.end.strftime("%H:%M")
        time_range = f"{start_time} - {end_time}"
        
        duration = f"{block.duration_minutes}m"
        
        # Use text-based indicators instead of emojis for better Windows compatibility
        type_map = {
            'pomodoro': 'WORK',
            'break': 'BREAK',
            'long_break': 'LONG-BREAK',
            'event': 'EVENT'
        }
        type_display = type_map.get(block.type, 'UNKNOWN')
        
        table.add_row(time_range, duration, type_display, block.title)
    
    console.print(table)
    
    # Display summary
    summary_text = f"""
** Plan Summary **
• Total Pomodoros: {summary.total_pomodoros}
• Break Time: {summary.total_break_time} minutes
• Scheduled Tasks: {summary.scheduled_tasks}
• Free Time: {summary.free_time_minutes} minutes
"""
    
    if summary.current_time_used:
        summary_text += "• TIME: Started from current time (not workday start)\n"
    
    if summary.unscheduled_tasks:
        summary_text += f"• WARNING: Unscheduled: {', '.join(summary.unscheduled_tasks)}\n"
    
    if summary.deep_work_windows:
        summary_text += f"• FOCUS: Deep Work: {', '.join(summary.deep_work_windows)}\n"
    
    console.print(Panel(summary_text, title="Summary", border_style="blue"))
    
    # Display tomorrow suggestions if any
    if summary.tomorrow_suggestions:
        tomorrow_text = "\n".join([f"• {suggestion}" for suggestion in summary.tomorrow_suggestions])
        console.print(Panel(
            tomorrow_text, 
            title="Suggested for Tomorrow", 
            border_style="yellow"
        ))


@app.command()
def plan(
    plan_file: Path = typer.Argument(..., help="JSON file with plan request"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save plan to JSON file"),
    ics: Optional[Path] = typer.Option(None, "--ics", help="Export to ICS file"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output"),
    start_from_now: bool = typer.Option(True, "--start-from-now/--start-from-workday", help="Start planning from current time vs workday start")
):
    """Generate a day plan from tasks and events"""
    
    # Load and process plan
    request = load_plan_request(plan_file)
    response = plan_day(request, start_from_now=start_from_now)
    
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
    save_log: bool = typer.Option(True, "--save/--no-save", help="Save session log"),
    start_from_now: bool = typer.Option(True, "--start-from-now/--start-from-workday", help="Start planning from current time vs workday start")
):
    """Generate plan and run timer"""
    
    # Load and process plan
    request = load_plan_request(plan_file)
    response = plan_day(request, start_from_now=start_from_now)
    
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
    """Run timer on existing plan"""
    
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
    """Show current timer status"""
    rprint("Timer status functionality not yet implemented")
    rprint("Use 'aida run' or 'aida timer' to start a session")


@app.command()
def storage():
    """Show storage locations and saved files"""
    from .storage import get_storage_stats, AIDA_DIR
    import os
    
    stats = get_storage_stats()
    
    console.print(Panel(
        f"[bold cyan]AIDA Storage Information[/bold cyan]",
        style="blue"
    ))
    
    console.print(f"\n[bold]Storage Directory:[/bold] {stats['storage_dir']}")
    console.print(f"[bold]Preferences File:[/bold] {'Exists' if stats['preferences_exists'] else 'Missing'}")
    
    # Show session logs
    if stats['log_files']:
        console.print(f"\n[bold]Session Logs:[/bold]")
        for log_info in stats['log_files']:
            console.print(f"  • {log_info['date']}: {log_info['entries']} sessions")
        console.print(f"  [dim]Total: {stats['total_log_entries']} logged sessions[/dim]")
    else:
        console.print("\n[bold]Session Logs:[/bold] No logs found")
    
    # Show JARVIS generated plans
    plans_dir = AIDA_DIR / "plans"
    if plans_dir.exists():
        plan_files = list(plans_dir.glob("*.json"))
        if plan_files:
            console.print(f"\n[bold]JARVIS Generated Plans:[/bold]")
            # Sort by modification time (newest first)
            plan_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for plan_file in plan_files[:10]:  # Show latest 10
                mtime = os.path.getctime(plan_file)
                from datetime import datetime
                date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                console.print(f"  • {plan_file.name} ({date_str})")
            if len(plan_files) > 10:
                console.print(f"  [dim]... and {len(plan_files) - 10} more[/dim]")
            console.print(f"  [dim]Location: {plans_dir}[/dim]")
        else:
            console.print(f"\n[bold]JARVIS Generated Plans:[/bold] None yet")
    else:
        console.print(f"\n[bold]JARVIS Generated Plans:[/bold] None yet")
    
    # Show database info if exists
    if stats.get('sqlite_sessions', 0) > 0:
        console.print(f"\n[bold]Database Sessions:[/bold] {stats['sqlite_sessions']}")
    
    console.print("\n[bold]Tips:[/bold]")
    console.print("  • Session logs are created when you run timers")
    console.print("  • JARVIS plans are auto-saved when generated")
    console.print("  • Use 'aida plan' to load existing JSON files")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current preferences"),
    workday_start: Optional[str] = typer.Option(None, help="Set workday start (HH:MM)"),
    workday_end: Optional[str] = typer.Option(None, help="Set workday end (HH:MM)"),
    pomodoro_min: Optional[int] = typer.Option(None, help="Set pomodoro duration"),
):
    """Manage AIDA configuration"""
    
    if show:
        try:
            prefs = load_preferences()
            table = Table(title="AIDA Configuration")
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
        rprint("Configuration management not fully implemented yet")
        rprint("Edit examples/today.json to customize preferences for now")


@app.command()
def assistant():
    """Start JARVIS-style conversational planning assistant"""
    try:
        start_jarvis_assistant()
    except KeyboardInterrupt:
        rprint("\nPlanning session ended. See you next time!")
    except Exception as e:
        rprint(f"Error starting assistant: {e}")
        rprint("Make sure your OPENAI_API_KEY is set in the .env file")


@app.command()
def chat(
    input_text: str = typer.Argument(..., help="Natural language description of your day"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save generated plan to JSON file")
):
    """Quick natural language planning (single-shot mode)"""
    rprint("AIDA Quick Planning Mode")
    rprint(f"Processing: {input_text}")
    
    try:
        from .assistant import JarvisAssistant
        assistant = JarvisAssistant()
        
        # Get response from JARVIS for single input
        response = assistant._get_jarvis_response(input_text)
        
        if "PLAN_READY:" in response:
            parts = response.split("PLAN_READY:", 1)
            json_data = parts[1].strip()
            
            plan_response = assistant._generate_plan_from_json(json_data)
            if plan_response:
                display_plan(plan_response.blocks, plan_response.summary)
                
                # Save to file if requested
                if output:
                    plan_data = {
                        "preferences": plan_response.summary.model_dump() if hasattr(plan_response.summary, 'model_dump') else {},
                        "tasks": [{"title": block.title, "estimate_min": block.duration_minutes} 
                                for block in plan_response.blocks if block.type == "pomodoro"],
                        "events": [{"title": block.title, "start": block.start.isoformat(), "end": block.end.isoformat()}
                                 for block in plan_response.blocks if block.type == "event"]
                    }
                    with open(output, 'w') as f:
                        json.dump(plan_data, f, indent=2, default=str)
                    rprint(f"Plan saved to {output}")
            else:
                rprint("Could not generate plan from the input. Try the interactive mode: `aida assistant`")
        else:
            rprint(f"AIDA: {response}")
            rprint("For full planning, try: `aida assistant` for interactive mode")
            
    except Exception as e:
        rprint(f"Error: {e}")
        rprint("Try the interactive mode: `aida assistant`")


@app.command()
def version():
    """Show AIDA version"""
    from . import __version__
    rprint(f"AIDA v{__version__}")


if __name__ == "__main__":
    app()