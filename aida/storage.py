"""Storage functionality for AIDA - preferences and session logs"""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional
import os

from .models import Preferences, SessionLog, PlanSummary, Block


# Default storage directory
AIDA_DIR = Path.home() / ".aida"
PREFS_FILE = AIDA_DIR / "prefs.json"
LOGS_DIR = AIDA_DIR / "logs"
DB_FILE = AIDA_DIR / "aida.db"


def ensure_storage_dirs():
    """Ensure storage directories exist"""
    AIDA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)


def get_default_preferences() -> Preferences:
    """Get default preferences for new users"""
    now = datetime.now(timezone.utc)
    workday_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    workday_end = now.replace(hour=17, minute=30, second=0, microsecond=0)
    
    return Preferences(
        workday_start=workday_start,
        workday_end=workday_end,
        pomodoro_min=25,
        break_min=5,
        long_break_min=15,
        cycles_per_long_break=4
    )


def load_preferences() -> Preferences:
    """Load user preferences from storage"""
    ensure_storage_dirs()
    
    if not PREFS_FILE.exists():
        # Create default preferences file
        default_prefs = get_default_preferences()
        save_preferences(default_prefs)
        return default_prefs
    
    try:
        with open(PREFS_FILE, 'r') as f:
            data = json.load(f)
        return Preferences.model_validate(data)
    except Exception as e:
        print(f"Warning: Error loading preferences, using defaults: {e}")
        return get_default_preferences()


def save_preferences(preferences: Preferences):
    """Save user preferences to storage"""
    ensure_storage_dirs()
    
    try:
        with open(PREFS_FILE, 'w') as f:
            json.dump(preferences.model_dump(), f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving preferences: {e}")


def save_session_log(blocks: List[Block], completed_blocks: List[int], summary: PlanSummary, notes: Optional[str] = None):
    """Save session log to JSONL file"""
    ensure_storage_dirs()
    
    session_log = SessionLog(
        blocks=blocks,
        completed_blocks=completed_blocks,
        summary=summary,
        notes=notes
    )
    
    # Save to daily JSONL file
    log_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{log_date}.jsonl"
    
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(session_log.model_dump(), default=str) + '\n')
    except Exception as e:
        print(f"Error saving session log: {e}")


def load_session_logs(date: Optional[str] = None) -> List[SessionLog]:
    """Load session logs for a specific date or today"""
    ensure_storage_dirs()
    
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    log_file = LOGS_DIR / f"{date}.jsonl"
    
    if not log_file.exists():
        return []
    
    sessions = []
    try:
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    sessions.append(SessionLog.model_validate(data))
    except Exception as e:
        print(f"Error loading session logs: {e}")
    
    return sessions


def init_sqlite_db():
    """Initialize SQLite database with tables (optional storage method)"""
    ensure_storage_dirs()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Preferences table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY,
            workday_start TEXT NOT NULL,
            workday_end TEXT NOT NULL,
            pomodoro_min INTEGER DEFAULT 25,
            break_min INTEGER DEFAULT 5,
            long_break_min INTEGER DEFAULT 15,
            cycles_per_long_break INTEGER DEFAULT 4,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            date TEXT NOT NULL,
            blocks TEXT NOT NULL,  -- JSON
            completed_blocks TEXT NOT NULL,  -- JSON array
            summary TEXT NOT NULL,  -- JSON
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Blocks table (normalized)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            block_index INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            task_id TEXT,
            completed BOOLEAN DEFAULT FALSE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
    ''')
    
    conn.commit()
    conn.close()


def save_session_to_db(blocks: List[Block], completed_blocks: List[int], summary: PlanSummary, notes: Optional[str] = None):
    """Save session log to SQLite database (alternative to JSONL)"""
    ensure_storage_dirs()
    init_sqlite_db()
    
    session_log = SessionLog(
        blocks=blocks,
        completed_blocks=completed_blocks,
        summary=summary,
        notes=notes
    )
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Insert session
        cursor.execute('''
            INSERT INTO sessions (session_id, date, blocks, completed_blocks, summary, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session_log.session_id,
            session_log.date.isoformat(),
            json.dumps([block.model_dump() for block in blocks], default=str),
            json.dumps(completed_blocks),
            json.dumps(summary.model_dump(), default=str),
            notes
        ))
        
        # Insert individual blocks
        for i, block in enumerate(blocks):
            cursor.execute('''
                INSERT INTO blocks (session_id, block_index, start_time, end_time, type, title, task_id, completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_log.session_id,
                i,
                block.start.isoformat(),
                block.end.isoformat(),
                block.type,
                block.title,
                block.task_id,
                i in completed_blocks
            ))
        
        conn.commit()
        
    except Exception as e:
        print(f"Error saving session to database: {e}")
        conn.rollback()
    finally:
        conn.close()


def get_storage_stats() -> dict:
    """Get statistics about stored data"""
    ensure_storage_dirs()
    
    stats = {
        "storage_dir": str(AIDA_DIR),
        "preferences_exists": PREFS_FILE.exists(),
        "log_files": [],
        "total_log_entries": 0
    }
    
    # Count log files and entries
    if LOGS_DIR.exists():
        for log_file in LOGS_DIR.glob("*.jsonl"):
            try:
                with open(log_file, 'r') as f:
                    line_count = sum(1 for line in f if line.strip())
                stats["log_files"].append({
                    "date": log_file.stem,
                    "entries": line_count
                })
                stats["total_log_entries"] += line_count
            except Exception:
                pass
    
    # SQLite database info
    if DB_FILE.exists():
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sessions")
            session_count = cursor.fetchone()[0]
            stats["sqlite_sessions"] = session_count
            conn.close()
        except Exception:
            stats["sqlite_sessions"] = "error"
    else:
        stats["sqlite_sessions"] = 0
    
    return stats


def cleanup_old_logs(days_to_keep: int = 30):
    """Clean up old log files (keep only recent days)"""
    ensure_storage_dirs()
    
    if not LOGS_DIR.exists():
        return
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d")
    
    removed_count = 0
    for log_file in LOGS_DIR.glob("*.jsonl"):
        if log_file.stem < cutoff_str:
            try:
                log_file.unlink()
                removed_count += 1
            except Exception as e:
                print(f"Error removing old log file {log_file}: {e}")
    
    if removed_count > 0:
        print(f"Cleaned up {removed_count} old log files")


# Export configuration paths for other modules
__all__ = [
    'AIDA_DIR', 'PREFS_FILE', 'LOGS_DIR', 'DB_FILE',
    'load_preferences', 'save_preferences', 
    'save_session_log', 'load_session_logs',
    'init_sqlite_db', 'save_session_to_db',
    'get_storage_stats', 'cleanup_old_logs'
]