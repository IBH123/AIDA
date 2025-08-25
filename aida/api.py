"""FastAPI application for AIDA"""

from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import json

from .models import PlanRequest, PlanResponse, Block, TimerState
from .planner import plan_day
from .timer import PomodoroTimer
from .ics import blocks_to_ics_content
from .storage import save_session_log

# Global timer instance (for simplicity in v0.1)
current_timer: Optional[PomodoroTimer] = None

app = FastAPI(
    title="AIDA API",
    description="Adaptive Intelligent Day Assistant - REST API for day planning and Pomodoro timer",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/v1/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest, start_from_now: bool = True):
    """Generate a day plan from tasks and events"""
    try:
        response = plan_day(request, start_from_now=start_from_now)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Planning error: {str(e)}")


@app.get("/v1/plan/ics")
async def export_plan_ics(
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    blocks_json: Optional[str] = None
):
    """Export plan as ICS calendar file
    
    Args:
        from_time: ISO timestamp to filter from (optional)
        to_time: ISO timestamp to filter to (optional) 
        blocks_json: JSON string of blocks array (required if no current timer)
    """
    
    blocks = []
    
    # Try to get blocks from current timer first
    if current_timer and current_timer.blocks:
        blocks = current_timer.blocks
    elif blocks_json:
        try:
            blocks_data = json.loads(blocks_json)
            blocks = [Block.model_validate(block) for block in blocks_data]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid blocks JSON: {str(e)}")
    else:
        raise HTTPException(
            status_code=400, 
            detail="No blocks available. Start a timer or provide blocks_json parameter."
        )
    
    # Filter blocks by time range if specified
    if from_time or to_time:
        filtered_blocks = []
        for block in blocks:
            include = True
            
            if from_time:
                try:
                    from_dt = datetime.fromisoformat(from_time.replace('Z', '+00:00'))
                    if block.start < from_dt:
                        include = False
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid from_time format")
            
            if to_time and include:
                try:
                    to_dt = datetime.fromisoformat(to_time.replace('Z', '+00:00'))
                    if block.end > to_dt:
                        include = False
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid to_time format")
            
            if include:
                filtered_blocks.append(block)
        
        blocks = filtered_blocks
    
    if not blocks:
        raise HTTPException(status_code=404, detail="No blocks found in specified time range")
    
    try:
        ics_content = blocks_to_ics_content(blocks)
        return Response(
            content=ics_content,
            media_type="text/calendar",
            headers={"Content-Disposition": "attachment; filename=aida-plan.ics"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ICS export error: {str(e)}")


@app.post("/v1/timer/start")
async def start_timer(
    background_tasks: BackgroundTasks,
    blocks: List[Block],
    start_index: int = 0,
    use_tts: bool = False
):
    """Start timer with blocks (runs in background)
    
    Note: In v0.1, this is a simplified implementation.
    The timer runs in the background but API responses are immediate.
    """
    global current_timer
    
    if current_timer and current_timer.state.is_running:
        raise HTTPException(status_code=409, detail="Timer already running")
    
    if start_index >= len(blocks):
        raise HTTPException(status_code=400, detail="Invalid start_index")
    
    try:
        # Create and start timer
        current_timer = PomodoroTimer(blocks, use_tts=use_tts)
        
        # Run timer in background
        background_tasks.add_task(current_timer.start, start_index)
        
        return {
            "status": "started",
            "total_blocks": len(blocks),
            "start_index": start_index,
            "message": "Timer started in background"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Timer start error: {str(e)}")


@app.post("/v1/timer/stop")
async def stop_timer():
    """Stop the current timer"""
    global current_timer
    
    if not current_timer:
        raise HTTPException(status_code=404, detail="No timer found")
    
    current_timer.stop()
    
    return {
        "status": "stopped",
        "message": "Timer stopped successfully"
    }


@app.post("/v1/timer/pause")
async def pause_timer():
    """Pause the current timer"""
    global current_timer
    
    if not current_timer:
        raise HTTPException(status_code=404, detail="No timer found")
    
    if not current_timer.state.is_running:
        raise HTTPException(status_code=400, detail="Timer is not running")
    
    current_timer.pause()
    
    return {
        "status": "paused",
        "message": "Timer paused successfully"
    }


@app.post("/v1/timer/resume")
async def resume_timer(background_tasks: BackgroundTasks):
    """Resume the paused timer"""
    global current_timer
    
    if not current_timer:
        raise HTTPException(status_code=404, detail="No timer found")
    
    if current_timer.state.is_running:
        raise HTTPException(status_code=400, detail="Timer is already running")
    
    # Resume timer in background
    background_tasks.add_task(current_timer.resume)
    
    return {
        "status": "resumed",
        "message": "Timer resumed successfully"
    }


@app.get("/v1/timer/status")
async def get_timer_status():
    """Get current timer status"""
    global current_timer
    
    if not current_timer:
        return {
            "timer_exists": False,
            "message": "No timer found"
        }
    
    progress = current_timer.get_progress()
    current_block = current_timer.get_current_block()
    
    return {
        "timer_exists": True,
        "is_running": current_timer.state.is_running,
        "current_block_index": current_timer.state.current_block_index,
        "current_block": current_block.model_dump() if current_block else None,
        "progress": progress,
        "start_time": current_timer.state.start_time.isoformat() if current_timer.state.start_time else None,
        "completed_blocks": current_timer.state.completed_blocks
    }


@app.post("/v1/timer/skip")
async def skip_current_block():
    """Skip the current timer block"""
    global current_timer
    
    if not current_timer:
        raise HTTPException(status_code=404, detail="No timer found")
    
    if not current_timer.state.is_running:
        raise HTTPException(status_code=400, detail="Timer is not running")
    
    current_block = current_timer.get_current_block()
    current_timer.skip_current_block()
    
    return {
        "status": "skipped",
        "skipped_block": current_block.title if current_block else "Unknown",
        "new_block_index": current_timer.state.current_block_index
    }


@app.get("/v1/summary/today")
async def get_today_summary():
    """Get summary of today's completed sessions"""
    global current_timer
    
    if not current_timer:
        return {
            "message": "No timer session found",
            "summary": None
        }
    
    progress = current_timer.get_progress()
    
    pomodoros_completed = len([
        i for i in current_timer.state.completed_blocks
        if i < len(current_timer.blocks) and current_timer.blocks[i].type == 'pomodoro'
    ])
    
    summary = {
        "date": datetime.now().date().isoformat(),
        "total_blocks": progress["total_blocks"],
        "completed_blocks": progress["completed_blocks"],
        "pomodoros_completed": pomodoros_completed,
        "progress_percent": progress["progress_percent"],
        "session_duration_minutes": None
    }
    
    if current_timer.state.start_time:
        duration = datetime.utcnow() - current_timer.state.start_time.replace(tzinfo=None)
        summary["session_duration_minutes"] = int(duration.total_seconds() / 60)
    
    return {
        "message": "Today's session summary",
        "summary": summary
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print("🚀 AIDA API starting up...")


@app.on_event("shutdown") 
async def shutdown_event():
    """Application shutdown event"""
    global current_timer
    if current_timer and current_timer.state.is_running:
        current_timer.stop()
    print("👋 AIDA API shutting down...")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "AIDA API",
        "version": "0.1.0",
        "description": "Adaptive Intelligent Day Assistant",
        "docs_url": "/docs",
        "health_check": "/healthz",
        "endpoints": {
            "planning": "/v1/plan",
            "timer": "/v1/timer/*",
            "export": "/v1/plan/ics", 
            "summary": "/v1/summary/today"
        }
    }