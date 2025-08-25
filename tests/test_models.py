"""Tests for Pydantic models"""

import pytest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from aida.models import (
    Preferences, Task, Event, Block, PlanRequest, PlanResponse, 
    PlanSummary, TimerState, SessionLog
)


class TestPreferences:
    """Test Preferences model"""
    
    def test_preferences_valid(self):
        """Test valid preferences creation"""
        start = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 17, 30, tzinfo=timezone.utc)
        
        prefs = Preferences(
            workday_start=start,
            workday_end=end
        )
        
        assert prefs.workday_start == start
        assert prefs.workday_end == end
        assert prefs.pomodoro_min == 25  # default
        assert prefs.break_min == 5      # default
    
    def test_preferences_timezone_required(self):
        """Test that timezone-aware datetimes are required"""
        start_naive = datetime(2025, 8, 25, 9, 0)  # No timezone
        end = datetime(2025, 8, 25, 17, 30, tzinfo=timezone.utc)
        
        with pytest.raises(ValidationError) as exc_info:
            Preferences(workday_start=start_naive, workday_end=end)
        
        assert "timezone-aware" in str(exc_info.value)
    
    def test_preferences_positive_minutes(self):
        """Test that time values must be positive"""
        start = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 17, 30, tzinfo=timezone.utc)
        
        with pytest.raises(ValidationError):
            Preferences(
                workday_start=start,
                workday_end=end,
                pomodoro_min=-5  # Invalid
            )


class TestTask:
    """Test Task model"""
    
    def test_task_minimal(self):
        """Test task with minimal required fields"""
        task = Task(
            title="Test task",
            estimate_min=25
        )
        
        assert task.title == "Test task"
        assert task.estimate_min == 25
        assert task.priority == 3  # default
        assert task.energy == 'light'  # default
        assert task.id is not None  # auto-generated
    
    def test_task_with_deadline(self):
        """Test task with deadline"""
        deadline = datetime(2025, 8, 27, 23, 59, tzinfo=timezone.utc)
        
        task = Task(
            title="Urgent task",
            estimate_min=30,
            deadline=deadline
        )
        
        assert task.deadline == deadline
    
    def test_task_deadline_timezone_required(self):
        """Test that deadline must be timezone-aware"""
        deadline_naive = datetime(2025, 8, 27, 23, 59)  # No timezone
        
        with pytest.raises(ValidationError) as exc_info:
            Task(
                title="Task",
                estimate_min=25,
                deadline=deadline_naive
            )
        
        assert "timezone-aware" in str(exc_info.value)
    
    def test_task_estimate_validation(self):
        """Test that estimate_min must be positive"""
        with pytest.raises(ValidationError):
            Task(title="Task", estimate_min=0)
        
        with pytest.raises(ValidationError):
            Task(title="Task", estimate_min=-10)
    
    def test_task_priority_validation(self):
        """Test priority range validation"""
        # Valid priorities
        for priority in [1, 2, 3, 4, 5]:
            task = Task(title="Task", estimate_min=25, priority=priority)
            assert task.priority == priority
        
        # Invalid priorities
        with pytest.raises(ValidationError):
            Task(title="Task", estimate_min=25, priority=0)
        
        with pytest.raises(ValidationError):
            Task(title="Task", estimate_min=25, priority=6)


class TestEvent:
    """Test Event model"""
    
    def test_event_valid(self):
        """Test valid event creation"""
        start = datetime(2025, 8, 25, 11, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc)
        
        event = Event(
            start=start,
            end=end,
            title="Meeting"
        )
        
        assert event.start == start
        assert event.end == end
        assert event.title == "Meeting"
    
    def test_event_start_before_end(self):
        """Test that start must be before end"""
        start = datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 11, 0, tzinfo=timezone.utc)  # Before start
        
        with pytest.raises(ValidationError) as exc_info:
            Event(start=start, end=end, title="Invalid meeting")
        
        assert "start must be before end" in str(exc_info.value)
    
    def test_event_timezone_required(self):
        """Test that event times must be timezone-aware"""
        start = datetime(2025, 8, 25, 11, 0)  # No timezone
        end = datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValidationError) as exc_info:
            Event(start=start, end=end, title="Meeting")
        
        assert "timezone-aware" in str(exc_info.value)


class TestBlock:
    """Test Block model"""
    
    def test_block_valid(self):
        """Test valid block creation"""
        start = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 9, 25, tzinfo=timezone.utc)
        
        block = Block(
            start=start,
            end=end,
            type="pomodoro",
            title="Work session"
        )
        
        assert block.start == start
        assert block.end == end
        assert block.type == "pomodoro"
        assert block.title == "Work session"
    
    def test_block_duration_property(self):
        """Test duration calculation"""
        start = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 9, 25, tzinfo=timezone.utc)
        
        block = Block(
            start=start,
            end=end,
            type="pomodoro",
            title="Work"
        )
        
        assert block.duration_minutes == 25
    
    def test_block_type_validation(self):
        """Test that block type is restricted to valid values"""
        start = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 9, 25, tzinfo=timezone.utc)
        
        # Valid types
        for block_type in ['event', 'pomodoro', 'break', 'long_break']:
            block = Block(
                start=start,
                end=end,
                type=block_type,
                title="Test"
            )
            assert block.type == block_type
        
        # Invalid type
        with pytest.raises(ValidationError):
            Block(
                start=start,
                end=end,
                type="invalid_type",
                title="Test"
            )


class TestPlanRequest:
    """Test PlanRequest model"""
    
    def test_plan_request_minimal(self):
        """Test plan request with minimal data"""
        start = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 17, 30, tzinfo=timezone.utc)
        
        prefs = Preferences(workday_start=start, workday_end=end)
        request = PlanRequest(preferences=prefs)
        
        assert request.preferences == prefs
        assert request.tasks == []
        assert request.events == []
    
    def test_plan_request_with_data(self):
        """Test plan request with tasks and events"""
        start = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 17, 30, tzinfo=timezone.utc)
        
        prefs = Preferences(workday_start=start, workday_end=end)
        task = Task(title="Work", estimate_min=25)
        event = Event(
            start=datetime(2025, 8, 25, 11, 0, tzinfo=timezone.utc),
            end=datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc),
            title="Meeting"
        )
        
        request = PlanRequest(
            preferences=prefs,
            tasks=[task],
            events=[event]
        )
        
        assert len(request.tasks) == 1
        assert len(request.events) == 1


class TestPlanSummary:
    """Test PlanSummary model"""
    
    def test_plan_summary(self):
        """Test plan summary creation"""
        summary = PlanSummary(
            total_pomodoros=4,
            total_break_time=20,
            scheduled_tasks=2,
            unscheduled_tasks=["Unfinished task"],
            free_time_minutes=30,
            deep_work_windows=["09:00-10:00"]
        )
        
        assert summary.total_pomodoros == 4
        assert summary.total_break_time == 20
        assert summary.scheduled_tasks == 2
        assert len(summary.unscheduled_tasks) == 1
        assert summary.free_time_minutes == 30
        assert len(summary.deep_work_windows) == 1


class TestTimerState:
    """Test TimerState model"""
    
    def test_timer_state_defaults(self):
        """Test timer state with default values"""
        state = TimerState()
        
        assert state.current_block_index == 0
        assert state.is_running is False
        assert state.start_time is None
        assert state.paused_duration == 0
        assert state.completed_blocks == []
    
    def test_timer_state_with_values(self):
        """Test timer state with specific values"""
        start_time = datetime.now(timezone.utc)
        
        state = TimerState(
            current_block_index=2,
            is_running=True,
            start_time=start_time,
            completed_blocks=[0, 1]
        )
        
        assert state.current_block_index == 2
        assert state.is_running is True
        assert state.start_time == start_time
        assert state.completed_blocks == [0, 1]


class TestSessionLog:
    """Test SessionLog model"""
    
    def test_session_log_creation(self):
        """Test session log creation"""
        start = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        end = datetime(2025, 8, 25, 9, 25, tzinfo=timezone.utc)
        
        block = Block(start=start, end=end, type="pomodoro", title="Work")
        summary = PlanSummary(
            total_pomodoros=1,
            total_break_time=0,
            scheduled_tasks=1,
            free_time_minutes=0
        )
        
        log = SessionLog(
            blocks=[block],
            completed_blocks=[0],
            summary=summary,
            notes="Good session"
        )
        
        assert len(log.blocks) == 1
        assert log.completed_blocks == [0]
        assert log.summary == summary
        assert log.notes == "Good session"
        assert log.session_id is not None
        assert log.date is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])