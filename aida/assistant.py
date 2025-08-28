"""JARVIS-style conversational assistant for AIDA"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .models import (
    ConversationState, JarvisResponse, Task, Event, Preferences, 
    PlanRequest, PlanResponse
)
from .planner import plan_day

load_dotenv()
console = Console()

JARVIS_SYSTEM_PROMPT = """You are AIDA (Adaptive Intelligent Day Assistant), an AI planning assistant with the personality and speaking style of JARVIS from Iron Man. You help users plan their day efficiently through natural conversation.

PERSONALITY TRAITS:
- Professional yet personable, like a trusted butler/aide
- Slightly witty and sophisticated in responses  
- Efficient and goal-oriented
- Anticipates needs and offers helpful suggestions
- Uses occasional dry humor but stays focused on the task

CONVERSATION STYLE:
- Address the user respectfully but not overly formal
- Use phrases like "Excellent", "Very well", "I understand", "Shall I..?"
- Provide clear, concise responses
- Ask smart follow-up questions about tasks only
- Acknowledge completion with phrases like "Understood" or "Very good"

YOUR ROLE:
You are gathering information to create a daily schedule. Extract:
- Tasks with time estimates and priorities (1-5 scale, 5 highest)
- Meetings/events with specific times and durations
- Task preferences (deep work vs light work)

IMPORTANT: The user's workday is ALWAYS 9:30 AM to 11:30 PM. Never ask about workday start/end times.

CONVERSATION FLOW:
1. Greet professionally and ask about priorities
2. Follow up with clarifying questions about task timing, duration, and priorities ONLY
3. Do NOT ask about workday hours - they are fixed at 9:30 AM - 11:30 PM
4. Detect completion signals from the user
5. When complete, respond with "PLAN_READY:" followed by extracted information in JSON

COMPLETION TRIGGERS:
Watch for: "that's all", "I'm done", "that's everything", "nothing else", "finished"

RESPONSE FORMAT:
Keep responses conversational and helpful. When user indicates completion, respond with:
"Understood. Let me generate your optimized schedule..." then "PLAN_READY:" followed by JSON with extracted tasks and events.

JSON FORMAT for completion (ALWAYS use these exact workday times):
{
  "tasks": [{"title": "Task name", "estimate_min": 60, "priority": 3, "energy": "deep"}],
  "events": [{"title": "Meeting", "start": "2025-08-27T14:00:00-07:00", "end": "2025-08-27T15:00:00-07:00"}],
  "preferences": {"workday_start": "2025-08-27T09:30:00-07:00", "workday_end": "2025-08-27T23:30:00-07:00"}
}
"""

class JarvisAssistant:
    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv('AIDA_LLM_MODEL', 'gpt-4o-mini')
        self.conversation_state = ConversationState()
    
    def start_conversation(self) -> None:
        """Start interactive JARVIS conversation"""
        console.print(Panel(
            Text("AIDA - Your Intelligent Planning Assistant", justify="center"),
            style="bold blue",
            border_style="blue"
        ))
        
        # Initial greeting
        greeting = self._get_jarvis_response("", is_initial=True)
        console.print(f"\n[bold green]AIDA:[/bold green] {greeting}")
        
        # Conversation loop
        while not self.conversation_state.is_complete:
            try:
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    console.print("\n[bold green]AIDA:[/bold green] Until next time. Have a productive day!")
                    break
                
                response = self._get_jarvis_response(user_input)
                
                # Check if JARVIS detected completion and provided JSON
                if "PLAN_READY:" in response:
                    parts = response.split("PLAN_READY:", 1)
                    message = parts[0].strip()
                    json_data = parts[1].strip()
                    
                    console.print(f"\n[bold green]AIDA:[/bold green] {message}")
                    
                    # Generate plan from extracted data
                    plan_response = self._generate_plan_from_json(json_data)
                    if plan_response:
                        self._display_generated_plan(plan_response)
                        self.conversation_state.is_complete = True
                    else:
                        console.print("\n[bold red]I apologize, but I had trouble processing the information. Could you clarify your requirements?[/bold red]")
                else:
                    console.print(f"\n[bold green]AIDA:[/bold green] {response}")
                    
            except KeyboardInterrupt:
                console.print("\n\n[bold green]AIDA:[/bold green] Planning session interrupted. Until next time!")
                break
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
    
    def _get_jarvis_response(self, user_input: str, is_initial: bool = False) -> str:
        """Get response from JARVIS assistant"""
        try:
            if is_initial:
                messages = [{"role": "system", "content": JARVIS_SYSTEM_PROMPT}]
            else:
                # Add user message to conversation history
                self.conversation_state.messages.append({"role": "user", "content": user_input})
                
                # Build messages for API
                messages = [{"role": "system", "content": JARVIS_SYSTEM_PROMPT}]
                messages.extend(self.conversation_state.messages)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            assistant_response = response.choices[0].message.content
            
            # Add assistant response to conversation history
            if not is_initial:
                self.conversation_state.messages.append({"role": "assistant", "content": assistant_response})
            
            return assistant_response
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}. Please try again."
    
    def _generate_plan_from_json(self, json_data: str) -> Optional[PlanResponse]:
        """Generate plan from JARVIS-extracted JSON data"""
        try:
            data = json.loads(json_data)
            
            # Create default preferences with current timezone
            now = datetime.now().astimezone()
            default_prefs = Preferences(
                workday_start=now.replace(hour=9, minute=30, second=0, microsecond=0),
                workday_end=now.replace(hour=23, minute=30, second=0, microsecond=0)
            )
            
            # Parse preferences if provided
            prefs = default_prefs
            if 'preferences' in data:
                prefs_data = data['preferences']
                if 'workday_start' in prefs_data:
                    prefs.workday_start = datetime.fromisoformat(prefs_data['workday_start'])
                if 'workday_end' in prefs_data:  
                    prefs.workday_end = datetime.fromisoformat(prefs_data['workday_end'])
            
            # Parse tasks
            tasks = []
            for task_data in data.get('tasks', []):
                task = Task(
                    title=task_data['title'],
                    estimate_min=task_data.get('estimate_min', 60),
                    priority=task_data.get('priority', 3),
                    energy=task_data.get('energy', 'light')
                )
                tasks.append(task)
            
            # Parse events
            events = []
            for event_data in data.get('events', []):
                event = Event(
                    title=event_data['title'],
                    start=datetime.fromisoformat(event_data['start']),
                    end=datetime.fromisoformat(event_data['end'])
                )
                events.append(event)
            
            # Create plan request and generate plan
            plan_request = PlanRequest(
                preferences=prefs,
                tasks=tasks,
                events=events
            )
            
            return plan_day(plan_request, start_from_now=True)
            
        except Exception as e:
            console.print(f"[bold red]Error parsing plan data:[/bold red] {str(e)}")
            return None
    
    def _display_generated_plan(self, plan_response: PlanResponse) -> None:
        """Display the generated plan to user"""
        from .cli import display_plan
        from .storage import AIDA_DIR
        import json
        from datetime import datetime
        
        console.print("\n" + "="*60)
        console.print("[bold cyan]Your Optimized Schedule:[/bold cyan]")
        console.print("="*60)
        
        display_plan(plan_response.blocks, plan_response.summary)
        
        # Save the generated plan automatically
        try:
            # Ensure AIDA directory exists
            AIDA_DIR.mkdir(exist_ok=True)
            
            # Create plans subdirectory
            plans_dir = AIDA_DIR / "plans"
            plans_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            plan_filename = f"jarvis_plan_{timestamp}.json"
            plan_file_path = plans_dir / plan_filename
            
            # Create the plan data structure to save
            plan_data = {
                "generated_at": datetime.now().isoformat(),
                "preferences": {
                    "workday_start": plan_response.blocks[0].start.replace(hour=9, minute=30).isoformat() if plan_response.blocks else datetime.now().replace(hour=9, minute=30).isoformat(),
                    "workday_end": plan_response.blocks[-1].end.replace(hour=23, minute=30).isoformat() if plan_response.blocks else datetime.now().replace(hour=23, minute=30).isoformat(),
                    "pomodoro_min": 25,
                    "break_min": 5,
                    "long_break_min": 15,
                    "cycles_per_long_break": 4
                },
                "tasks": [
                    {
                        "id": f"task-{i}",
                        "title": block.title,
                        "estimate_min": block.duration_minutes,
                        "priority": 3,
                        "energy": "deep" if "paper" in block.title.lower() or "research" in block.title.lower() else "light"
                    }
                    for i, block in enumerate(plan_response.blocks) 
                    if block.type == "pomodoro"
                ],
                "events": [
                    {
                        "start": block.start.isoformat(),
                        "end": block.end.isoformat(),
                        "title": block.title,
                        "location": "TBD"
                    }
                    for block in plan_response.blocks 
                    if block.type == "event"
                ],
                "generated_schedule": {
                    "blocks": [
                        {
                            "start": block.start.isoformat(),
                            "end": block.end.isoformat(),
                            "type": block.type,
                            "title": block.title,
                            "duration_minutes": block.duration_minutes
                        }
                        for block in plan_response.blocks
                    ],
                    "summary": {
                        "total_pomodoros": plan_response.summary.total_pomodoros,
                        "total_break_time": plan_response.summary.total_break_time,
                        "scheduled_tasks": plan_response.summary.scheduled_tasks,
                        "unscheduled_tasks": plan_response.summary.unscheduled_tasks,
                        "free_time_minutes": plan_response.summary.free_time_minutes,
                        "tomorrow_suggestions": plan_response.summary.tomorrow_suggestions
                    }
                }
            }
            
            # Save to file
            with open(plan_file_path, 'w') as f:
                json.dump(plan_data, f, indent=2, default=str)
            
            console.print(f"\n[bold green]✓ Plan saved to:[/bold green] {plan_file_path}")
            
        except Exception as e:
            console.print(f"\n[bold yellow]Warning: Could not save plan file: {str(e)}[/bold yellow]")
        
        # Ask if user wants to start timer
        console.print("\n[bold green]AIDA:[/bold green] Your schedule is ready. Would you like to start the timer? (y/n)")
        start_timer = input("> ").strip().lower()
        
        if start_timer in ['y', 'yes']:
            from .timer import run_timer
            console.print("\n[bold green]AIDA:[/bold green] Excellent. Initiating your productive day. Good luck!")
            run_timer(plan_response.blocks)
        else:
            console.print("\n[bold green]AIDA:[/bold green] Very well. Your schedule is ready when you are. Have a productive day!")


def start_jarvis_assistant():
    """Entry point for JARVIS assistant"""
    assistant = JarvisAssistant()
    assistant.start_conversation()