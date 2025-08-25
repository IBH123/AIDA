"""Core planning algorithm for AIDA"""

from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import math
from .models import (
    Task, Event, Block, Preferences, PlanRequest, PlanResponse, PlanSummary
)


def merge_intervals(intervals: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    """Merge overlapping time intervals"""
    if not intervals:
        return []
    
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    
    for current in sorted_intervals[1:]:
        last = merged[-1]
        if current[0] <= last[1]:
            # Overlapping intervals, merge them
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)
    
    return merged


def subtract_busy_time(
    work_window: Tuple[datetime, datetime],
    busy_intervals: List[Tuple[datetime, datetime]]
) -> List[Tuple[datetime, datetime]]:
    """Subtract busy time from work window to get free intervals"""
    if not busy_intervals:
        return [work_window]
    
    # Merge overlapping busy intervals
    merged_busy = merge_intervals(busy_intervals)
    
    # Find free intervals
    free_intervals = []
    current_start = work_window[0]
    
    for busy_start, busy_end in merged_busy:
        # If there's a gap before this busy period
        if current_start < busy_start:
            free_intervals.append((current_start, busy_start))
        
        # Move start to after this busy period
        current_start = max(current_start, busy_end)
    
    # Add remaining time after last busy period
    if current_start < work_window[1]:
        free_intervals.append((current_start, work_window[1]))
    
    return free_intervals


def add_event_buffers(events: List[Event], buffer_minutes: int = 5) -> List[Tuple[datetime, datetime]]:
    """Add buffers around events to create busy intervals"""
    busy_intervals = []
    buffer_delta = timedelta(minutes=buffer_minutes)
    
    for event in events:
        buffered_start = event.start - buffer_delta
        buffered_end = event.end + buffer_delta
        busy_intervals.append((buffered_start, buffered_end))
    
    return busy_intervals


def calculate_task_score(task: Task, current_time: datetime) -> float:
    """Calculate priority score for a task"""
    base_score = 5 * task.priority
    
    # Urgency component
    urgency = 0
    if task.deadline:
        days_until_deadline = (task.deadline - current_time).days
        urgency = max(0, 10 - days_until_deadline)
    
    # Energy matching (prefer deep work in morning)
    energy_match = 0
    if task.requires_deep_work and 9 <= current_time.hour < 12:
        energy_match = 2
    
    return base_score + urgency + energy_match


def segment_task(task: Task, pomodoro_minutes: int) -> int:
    """Calculate number of pomodoro cycles needed for a task"""
    return math.ceil(task.estimate_min / pomodoro_minutes)


def create_pomodoro_block(
    start_time: datetime,
    duration_minutes: int,
    task: Task,
    block_type: str = "pomodoro"
) -> Block:
    """Create a pomodoro or break block"""
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    if block_type == "pomodoro":
        title = f"🍅 {task.title}"
        task_id = task.id
    elif block_type == "break":
        title = "☕ Break"
        task_id = None
    else:  # long_break
        title = "🌟 Long Break"
        task_id = None
    
    return Block(
        start=start_time,
        end=end_time,
        type=block_type,
        title=title,
        task_id=task_id
    )


def plan_day(request: PlanRequest) -> PlanResponse:
    """Generate a complete day plan from tasks and events"""
    prefs = request.preferences
    tasks = sorted(request.tasks, key=lambda t: calculate_task_score(t, prefs.workday_start), reverse=True)
    events = request.events
    
    # Create work window
    work_window = (prefs.workday_start, prefs.workday_end)
    
    # Add buffers around events and create busy intervals
    busy_intervals = add_event_buffers(events)
    
    # Add fixed events as busy intervals
    for event in events:
        busy_intervals.append((event.start, event.end))
    
    # Get free intervals
    free_intervals = subtract_busy_time(work_window, busy_intervals)
    
    # Create blocks for fixed events
    event_blocks = [
        Block(
            start=event.start,
            end=event.end,
            type="event",
            title=f"📅 {event.title}",
            task_id=None
        )
        for event in events
    ]
    
    # Pack tasks into free intervals
    all_blocks = event_blocks.copy()
    scheduled_task_ids = set()
    current_cycle_count = 0
    
    for free_start, free_end in free_intervals:
        current_time = free_start
        
        while current_time < free_end and tasks:
            # Find best task that fits
            best_task = None
            best_score = -1
            
            for task in tasks:
                if task.id in scheduled_task_ids:
                    continue
                
                cycles_needed = segment_task(task, prefs.pomodoro_min)
                time_needed = cycles_needed * (prefs.pomodoro_min + prefs.break_min)
                
                # Check if task fits in remaining free time
                remaining_minutes = (free_end - current_time).total_seconds() / 60
                if time_needed <= remaining_minutes:
                    score = calculate_task_score(task, current_time)
                    if score > best_score:
                        best_task = task
                        best_score = score
            
            if not best_task:
                break
            
            # Schedule the task
            cycles_needed = segment_task(best_task, prefs.pomodoro_min)
            
            for cycle in range(cycles_needed):
                # Add pomodoro block
                if current_time >= free_end:
                    break
                
                pomodoro_block = create_pomodoro_block(
                    current_time, prefs.pomodoro_min, best_task, "pomodoro"
                )
                all_blocks.append(pomodoro_block)
                current_time += timedelta(minutes=prefs.pomodoro_min)
                current_cycle_count += 1
                
                # Add break (except after last cycle of task and at end of day)
                if (cycle < cycles_needed - 1 or tasks.index(best_task) < len(tasks) - 1) and current_time < free_end:
                    # Determine break type
                    if current_cycle_count % prefs.cycles_per_long_break == 0:
                        break_duration = prefs.long_break_min
                        break_type = "long_break"
                    else:
                        break_duration = prefs.break_min
                        break_type = "break"
                    
                    break_block = create_pomodoro_block(
                        current_time, break_duration, best_task, break_type
                    )
                    all_blocks.append(break_block)
                    current_time += timedelta(minutes=break_duration)
            
            scheduled_task_ids.add(best_task.id)
            tasks.remove(best_task)
    
    # Sort all blocks by start time
    all_blocks.sort(key=lambda b: b.start)
    
    # Generate summary
    pomodoro_blocks = [b for b in all_blocks if b.type == "pomodoro"]
    break_blocks = [b for b in all_blocks if b.type in ["break", "long_break"]]
    unscheduled_tasks = [t.title for t in tasks]
    
    total_break_time = sum(b.duration_minutes for b in break_blocks)
    total_scheduled_time = sum(b.duration_minutes for b in all_blocks if b.type != "event")
    work_day_minutes = (prefs.workday_end - prefs.workday_start).total_seconds() / 60
    free_time = max(0, work_day_minutes - total_scheduled_time)
    
    deep_work_windows = [
        f"{b.start.strftime('%H:%M')}-{b.end.strftime('%H:%M')}"
        for b in pomodoro_blocks
        if b.task_id and any(t.requires_deep_work for t in request.tasks if t.id == b.task_id)
    ]
    
    summary = PlanSummary(
        total_pomodoros=len(pomodoro_blocks),
        total_break_time=total_break_time,
        scheduled_tasks=len(scheduled_task_ids),
        unscheduled_tasks=unscheduled_tasks,
        free_time_minutes=int(free_time),
        deep_work_windows=deep_work_windows
    )
    
    return PlanResponse(blocks=all_blocks, summary=summary)