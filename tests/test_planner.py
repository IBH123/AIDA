"""Tests for the planning algorithm"""

import pytest
from datetime import datetime, timezone, timedelta
from aida.models import Task, Event, Preferences, PlanRequest
from aida.planner import (
    plan_day, merge_intervals, subtract_busy_time, 
    calculate_task_score, segment_task, add_event_buffers
)


@pytest.fixture
def sample_preferences():
    """Sample preferences for testing"""
    start_time = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 8, 25, 17, 30, tzinfo=timezone.utc)
    
    return Preferences(
        workday_start=start_time,
        workday_end=end_time,
        pomodoro_min=25,
        break_min=5,
        long_break_min=15,
        cycles_per_long_break=4
    )


@pytest.fixture
def sample_tasks():
    """Sample tasks for testing"""
    deadline = datetime(2025, 8, 27, 23, 59, tzinfo=timezone.utc)
    
    return [
        Task(
            id="task-1",
            title="High priority task",
            estimate_min=50,
            priority=5,
            deadline=deadline,
            requires_deep_work=True
        ),
        Task(
            id="task-2", 
            title="Medium priority task",
            estimate_min=25,
            priority=3
        ),
        Task(
            id="task-3",
            title="Low priority task", 
            estimate_min=30,
            priority=1
        )
    ]


@pytest.fixture
def sample_events():
    """Sample events for testing"""
    return [
        Event(
            start=datetime(2025, 8, 25, 11, 0, tzinfo=timezone.utc),
            end=datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc),
            title="Team meeting",
            location="Zoom"
        ),
        Event(
            start=datetime(2025, 8, 25, 14, 30, tzinfo=timezone.utc),
            end=datetime(2025, 8, 25, 15, 0, tzinfo=timezone.utc),
            title="1:1 meeting"
        )
    ]


class TestIntervalOperations:
    """Test interval manipulation functions"""
    
    def test_merge_intervals_empty(self):
        """Test merging empty intervals list"""
        assert merge_intervals([]) == []
    
    def test_merge_intervals_non_overlapping(self):
        """Test merging non-overlapping intervals"""
        dt1 = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        dt2 = datetime(2025, 8, 25, 10, 0, tzinfo=timezone.utc)
        dt3 = datetime(2025, 8, 25, 11, 0, tzinfo=timezone.utc)
        dt4 = datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc)
        
        intervals = [(dt1, dt2), (dt3, dt4)]
        result = merge_intervals(intervals)
        
        assert len(result) == 2
        assert result == [(dt1, dt2), (dt3, dt4)]
    
    def test_merge_intervals_overlapping(self):
        """Test merging overlapping intervals"""
        dt1 = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        dt2 = datetime(2025, 8, 25, 10, 30, tzinfo=timezone.utc)
        dt3 = datetime(2025, 8, 25, 10, 0, tzinfo=timezone.utc)
        dt4 = datetime(2025, 8, 25, 11, 0, tzinfo=timezone.utc)
        
        intervals = [(dt1, dt2), (dt3, dt4)]
        result = merge_intervals(intervals)
        
        assert len(result) == 1
        assert result == [(dt1, dt4)]
    
    def test_subtract_busy_time(self):
        """Test subtracting busy time from work window"""
        work_start = datetime(2025, 8, 25, 9, 0, tzinfo=timezone.utc)
        work_end = datetime(2025, 8, 25, 17, 0, tzinfo=timezone.utc)
        work_window = (work_start, work_end)
        
        busy_start = datetime(2025, 8, 25, 11, 0, tzinfo=timezone.utc)
        busy_end = datetime(2025, 8, 25, 12, 0, tzinfo=timezone.utc)
        busy_intervals = [(busy_start, busy_end)]
        
        free_intervals = subtract_busy_time(work_window, busy_intervals)
        
        assert len(free_intervals) == 2
        assert free_intervals[0] == (work_start, busy_start)
        assert free_intervals[1] == (busy_end, work_end)
    
    def test_add_event_buffers(self, sample_events):
        """Test adding buffers around events"""
        busy_intervals = add_event_buffers(sample_events, buffer_minutes=5)
        
        assert len(busy_intervals) == 2
        
        # Check first event buffer
        expected_start = sample_events[0].start - timedelta(minutes=5)
        expected_end = sample_events[0].end + timedelta(minutes=5)
        assert busy_intervals[0] == (expected_start, expected_end)


class TestTaskOperations:
    """Test task-related functions"""
    
    def test_calculate_task_score_basic(self):
        """Test basic task scoring"""
        task = Task(
            title="Test task",
            estimate_min=25,
            priority=3
        )
        current_time = datetime(2025, 8, 25, 10, 0, tzinfo=timezone.utc)
        
        score = calculate_task_score(task, current_time)
        assert score == 15  # 5 * 3 priority, no deadline, no energy match
    
    def test_calculate_task_score_with_deadline(self):
        """Test task scoring with deadline urgency"""
        deadline = datetime(2025, 8, 26, 23, 59, tzinfo=timezone.utc)  # 1 day away
        task = Task(
            title="Urgent task",
            estimate_min=25,
            priority=3,
            deadline=deadline
        )
        current_time = datetime(2025, 8, 25, 10, 0, tzinfo=timezone.utc)
        
        score = calculate_task_score(task, current_time)
        assert score == 24  # 15 + 9 urgency (10 - 1 day)
    
    def test_calculate_task_score_deep_work_morning(self):
        """Test energy matching for deep work in morning"""
        task = Task(
            title="Deep work task",
            estimate_min=25,
            priority=3,
            requires_deep_work=True
        )
        morning_time = datetime(2025, 8, 25, 10, 0, tzinfo=timezone.utc)
        
        score = calculate_task_score(task, morning_time)
        assert score == 17  # 15 + 2 energy match
    
    def test_segment_task(self):
        """Test task segmentation into pomodoro cycles"""
        task = Task(title="Long task", estimate_min=60)
        cycles = segment_task(task, pomodoro_minutes=25)
        assert cycles == 3  # ceil(60/25) = 3
        
        task_short = Task(title="Short task", estimate_min=20)
        cycles_short = segment_task(task_short, pomodoro_minutes=25)
        assert cycles_short == 1


class TestPlanGeneration:
    """Test complete plan generation"""
    
    def test_plan_day_basic(self, sample_preferences, sample_tasks, sample_events):
        """Test basic day planning"""
        request = PlanRequest(
            preferences=sample_preferences,
            tasks=sample_tasks,
            events=sample_events
        )
        
        response = plan_day(request)
        
        assert response is not None
        assert len(response.blocks) > 0
        assert response.summary is not None
        
        # Check that all blocks have valid times
        for block in response.blocks:
            assert block.start < block.end
            assert block.start >= sample_preferences.workday_start
            assert block.end <= sample_preferences.workday_end
    
    def test_plan_day_no_tasks(self, sample_preferences, sample_events):
        """Test planning with only events, no tasks"""
        request = PlanRequest(
            preferences=sample_preferences,
            tasks=[],
            events=sample_events
        )
        
        response = plan_day(request)
        
        # Should still have event blocks
        event_blocks = [b for b in response.blocks if b.type == "event"]
        assert len(event_blocks) == len(sample_events)
        assert response.summary.total_pomodoros == 0
    
    def test_plan_day_no_events(self, sample_preferences, sample_tasks):
        """Test planning with tasks but no events"""
        request = PlanRequest(
            preferences=sample_preferences,
            tasks=sample_tasks,
            events=[]
        )
        
        response = plan_day(request)
        
        # Should have pomodoro blocks
        pomodoro_blocks = [b for b in response.blocks if b.type == "pomodoro"]
        assert len(pomodoro_blocks) > 0
        assert response.summary.scheduled_tasks > 0
    
    def test_plan_respects_event_times(self, sample_preferences, sample_tasks, sample_events):
        """Test that planning respects fixed event times"""
        request = PlanRequest(
            preferences=sample_preferences,
            tasks=sample_tasks,
            events=sample_events
        )
        
        response = plan_day(request)
        
        # Find event blocks
        event_blocks = [b for b in response.blocks if b.type == "event"]
        assert len(event_blocks) == 2
        
        # Check that events maintain their original times
        for i, event_block in enumerate(event_blocks):
            original_event = sample_events[i]
            assert event_block.start == original_event.start
            assert event_block.end == original_event.end
    
    def test_plan_includes_breaks(self, sample_preferences, sample_tasks):
        """Test that plan includes appropriate breaks"""
        request = PlanRequest(
            preferences=sample_preferences,
            tasks=sample_tasks,
            events=[]
        )
        
        response = plan_day(request)
        
        # Should have break blocks
        break_blocks = [b for b in response.blocks if b.type in ["break", "long_break"]]
        pomodoro_blocks = [b for b in response.blocks if b.type == "pomodoro"]
        
        # Should have breaks between pomodoros (not necessarily 1:1 ratio due to end-of-day logic)
        assert len(break_blocks) > 0
        assert len(pomodoro_blocks) > 0
    
    def test_plan_summary_accuracy(self, sample_preferences, sample_tasks):
        """Test that plan summary reflects actual scheduled content"""
        request = PlanRequest(
            preferences=sample_preferences,
            tasks=sample_tasks,
            events=[]
        )
        
        response = plan_day(request)
        
        # Count actual blocks
        pomodoro_blocks = [b for b in response.blocks if b.type == "pomodoro"]
        break_blocks = [b for b in response.blocks if b.type in ["break", "long_break"]]
        
        # Verify summary matches
        assert response.summary.total_pomodoros == len(pomodoro_blocks)
        
        actual_break_time = sum(b.duration_minutes for b in break_blocks)
        assert response.summary.total_break_time == actual_break_time
    
    def test_task_priority_ordering(self, sample_preferences):
        """Test that higher priority tasks are scheduled first"""
        high_priority = Task(title="High", estimate_min=25, priority=5)
        low_priority = Task(title="Low", estimate_min=25, priority=1)
        
        request = PlanRequest(
            preferences=sample_preferences,
            tasks=[low_priority, high_priority],  # Low priority first in input
            events=[]
        )
        
        response = plan_day(request)
        
        pomodoro_blocks = [b for b in response.blocks if b.type == "pomodoro"]
        
        # First pomodoro should be the high priority task
        if len(pomodoro_blocks) >= 2:
            first_task_id = pomodoro_blocks[0].task_id
            assert first_task_id == high_priority.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])