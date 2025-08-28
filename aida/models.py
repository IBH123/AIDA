"""Pydantic data models for AIDA"""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime, timezone
import uuid


class Preferences(BaseModel):
    """User preferences for day planning"""
    workday_start: datetime
    workday_end: datetime
    pomodoro_min: int = 25
    break_min: int = 5
    long_break_min: int = 15
    cycles_per_long_break: int = 4
    
    @field_validator('workday_start', 'workday_end')
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure datetime objects are timezone-aware"""
        if v.tzinfo is None:
            raise ValueError('Datetime must be timezone-aware')
        return v
    
    @field_validator('pomodoro_min', 'break_min', 'long_break_min')
    @classmethod
    def validate_positive_minutes(cls, v: int) -> int:
        """Ensure time values are positive"""
        if v <= 0:
            raise ValueError('Time values must be positive')
        return v


class Task(BaseModel):
    """A task to be scheduled"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    estimate_min: int = Field(ge=1, description="Estimated time in minutes")
    priority: int = Field(3, ge=1, le=5, description="Priority 1-5, 5 is highest")
    deadline: Optional[datetime] = None
    energy: Literal['deep', 'light'] = 'light'
    requires_deep_work: bool = False
    notes: Optional[str] = None
    
    @field_validator('deadline')
    @classmethod
    def validate_deadline_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure deadline is timezone-aware if provided"""
        if v is not None and v.tzinfo is None:
            raise ValueError('Deadline must be timezone-aware')
        return v


class Event(BaseModel):
    """A fixed calendar event"""
    start: datetime
    end: datetime
    title: str
    location: Optional[str] = None
    
    @field_validator('start', 'end')
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure datetime objects are timezone-aware"""
        if v.tzinfo is None:
            raise ValueError('Event times must be timezone-aware')
        return v
    
    def model_post_init(self, __context) -> None:
        """Validate that start is before end"""
        if self.start >= self.end:
            raise ValueError('Event start must be before end')


class Block(BaseModel):
    """A scheduled time block"""
    start: datetime
    end: datetime
    type: Literal['event', 'pomodoro', 'break', 'long_break']
    title: str
    task_id: Optional[str] = None
    
    @field_validator('start', 'end')
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure datetime objects are timezone-aware"""
        if v.tzinfo is None:
            raise ValueError('Block times must be timezone-aware')
        return v
    
    def model_post_init(self, __context) -> None:
        """Validate that start is before end"""
        if self.start >= self.end:
            raise ValueError('Block start must be before end')
    
    @property
    def duration_minutes(self) -> int:
        """Get block duration in minutes"""
        return int((self.end - self.start).total_seconds() / 60)


class PlanRequest(BaseModel):
    """Request to generate a day plan"""
    preferences: Preferences
    tasks: List[Task] = Field(default_factory=list)
    events: List[Event] = Field(default_factory=list)


class PlanSummary(BaseModel):
    """Summary of the generated plan"""
    total_pomodoros: int
    total_break_time: int
    scheduled_tasks: int
    unscheduled_tasks: List[str] = Field(default_factory=list)
    free_time_minutes: int
    deep_work_windows: List[str] = Field(default_factory=list)
    tomorrow_suggestions: List[str] = Field(default_factory=list)
    current_time_used: bool = False


class PlanResponse(BaseModel):
    """Response containing generated day plan"""
    blocks: List[Block]
    summary: PlanSummary


class TimerState(BaseModel):
    """Current state of the timer"""
    current_block_index: int = 0
    is_running: bool = False
    start_time: Optional[datetime] = None
    paused_duration: int = 0  # seconds
    completed_blocks: List[int] = Field(default_factory=list)
    current_block_actual_start: Optional[datetime] = None


class SessionLog(BaseModel):
    """Log entry for a completed session"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    blocks: List[Block]
    completed_blocks: List[int]
    summary: PlanSummary
    notes: Optional[str] = None


class ConversationState(BaseModel):
    """State management for JARVIS conversation"""
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Dict[str, str]] = Field(default_factory=list)
    extracted_tasks: List[Task] = Field(default_factory=list)
    extracted_events: List[Event] = Field(default_factory=list)
    preferences: Optional[Preferences] = None
    is_complete: bool = False
    completion_detected: bool = False


class JarvisResponse(BaseModel):
    """Structured response from JARVIS assistant"""
    message: str
    extracted_info: Dict[str, Any] = Field(default_factory=dict)
    is_completion: bool = False
    needs_clarification: bool = False
    suggested_actions: List[str] = Field(default_factory=list)