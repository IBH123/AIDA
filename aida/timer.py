"""Pomodoro timer implementation for AIDA"""

import time
import signal
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Callable
from .models import Block, TimerState, SessionLog


class PomodoroTimer:
    """Pomodoro timer with state management"""
    
    def __init__(self, blocks: List[Block], on_block_start: Optional[Callable] = None,
                 on_block_end: Optional[Callable] = None, use_tts: bool = False):
        self.blocks = blocks
        self.state = TimerState()
        self.on_block_start = on_block_start or self._default_block_start
        self.on_block_end = on_block_end or self._default_block_end
        self.use_tts = use_tts
        self._setup_signal_handlers()
        
        if use_tts:
            try:
                import pyttsx3
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
            except ImportError:
                print("Warning: pyttsx3 not available, disabling TTS")
                self.use_tts = False
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown on Ctrl+C"""
        def signal_handler(signum, frame):
            print("\n🛑 Timer stopped by user")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
    
    def _speak(self, text: str):
        """Speak text using TTS if enabled"""
        if self.use_tts and hasattr(self, 'tts_engine'):
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
    
    def _default_block_start(self, block: Block):
        """Default block start handler"""
        emoji_map = {
            'pomodoro': '🍅',
            'break': '☕',
            'long_break': '🌟',
            'event': '📅'
        }
        
        emoji = emoji_map.get(block.type, '⏰')
        start_time = block.start.strftime('%H:%M')
        end_time = block.end.strftime('%H:%M')
        duration = block.duration_minutes
        
        message = f"\n{emoji} Starting: {block.title}"
        message += f"\n⏰ Time: {start_time} - {end_time} ({duration} min)"
        
        if block.type == 'pomodoro':
            message += f"\n🎯 Focus on your task!"
        elif block.type in ['break', 'long_break']:
            message += f"\n😌 Time to relax!"
        
        print(message)
        print("=" * 50)
        
        # TTS for important blocks
        if block.type in ['pomodoro', 'long_break']:
            self._speak(f"Starting {block.title}")
    
    def _default_block_end(self, block: Block):
        """Default block end handler"""
        emoji_map = {
            'pomodoro': '✅',
            'break': '✨',
            'long_break': '🎉',
            'event': '✅'
        }
        
        emoji = emoji_map.get(block.type, '✅')
        message = f"{emoji} Completed: {block.title}"
        
        if block.type == 'pomodoro':
            message += " - Great work!"
        elif block.type in ['break', 'long_break']:
            message += " - Ready to focus?"
        
        print(f"\n{message}")
        
        # TTS for completions
        if block.type == 'pomodoro':
            self._speak("Pomodoro completed! Great work!")
        elif block.type == 'long_break':
            self._speak("Long break completed! Ready to focus?")
    
    def start(self, start_index: int = 0):
        """Start the timer from specified block index"""
        if not self.blocks:
            print("❌ No blocks to run!")
            return
        
        if start_index >= len(self.blocks):
            print(f"❌ Invalid start index: {start_index}")
            return
        
        self.state.current_block_index = start_index
        self.state.is_running = True
        self.state.start_time = datetime.now(timezone.utc)
        
        print(f"🚀 Starting timer with {len(self.blocks)} blocks")
        print(f"📍 Starting from block {start_index + 1}")
        
        try:
            while self.state.current_block_index < len(self.blocks) and self.state.is_running:
                current_block = self.blocks[self.state.current_block_index]
                
                # Skip events (they're just markers)
                if current_block.type == 'event':
                    print(f"\n📅 Event: {current_block.title}")
                    print(f"⏰ {current_block.start.strftime('%H:%M')} - {current_block.end.strftime('%H:%M')}")
                    self.state.completed_blocks.append(self.state.current_block_index)
                    self.state.current_block_index += 1
                    continue
                
                # Start block
                self.on_block_start(current_block)
                
                # Run timer for block duration
                duration_seconds = current_block.duration_minutes * 60
                self._run_countdown(duration_seconds, current_block)
                
                # End block
                if self.state.is_running:  # Only if not interrupted
                    self.on_block_end(current_block)
                    self.state.completed_blocks.append(self.state.current_block_index)
                    self.state.current_block_index += 1
                    
                    # Pause between blocks
                    if self.state.current_block_index < len(self.blocks):
                        print("\n⏸️  Press Enter to continue to next block...")
                        input()
            
            if self.state.is_running:
                print("\n🎉 All blocks completed! Great job!")
                self._show_session_summary()
        
        except KeyboardInterrupt:
            print("\n⏹️  Timer paused")
        finally:
            self.state.is_running = False
    
    def _run_countdown(self, duration_seconds: int, block: Block):
        """Run countdown timer for a block"""
        remaining = duration_seconds
        
        while remaining > 0 and self.state.is_running:
            mins, secs = divmod(remaining, 60)
            
            # Show progress every minute and in last 10 seconds
            if remaining % 60 == 0 or remaining <= 10:
                if remaining > 60:
                    print(f"⏳ {mins:02d}:{secs:02d} remaining")
                else:
                    print(f"⏳ {remaining} seconds...")
            
            time.sleep(1)
            remaining -= 1
    
    def stop(self):
        """Stop the timer"""
        self.state.is_running = False
        print("⏹️  Timer stopped")
    
    def pause(self):
        """Pause the timer"""
        self.state.is_running = False
        print("⏸️  Timer paused")
    
    def resume(self):
        """Resume the timer"""
        if not self.state.is_running and self.state.current_block_index < len(self.blocks):
            print("▶️  Resuming timer...")
            self.start(self.state.current_block_index)
    
    def skip_current_block(self):
        """Skip the current block"""
        if self.state.is_running and self.state.current_block_index < len(self.blocks):
            current_block = self.blocks[self.state.current_block_index]
            print(f"⏭️  Skipping: {current_block.title}")
            self.state.completed_blocks.append(self.state.current_block_index)
            self.state.current_block_index += 1
    
    def get_current_block(self) -> Optional[Block]:
        """Get the currently running block"""
        if 0 <= self.state.current_block_index < len(self.blocks):
            return self.blocks[self.state.current_block_index]
        return None
    
    def get_progress(self) -> dict:
        """Get timer progress information"""
        total_blocks = len(self.blocks)
        completed_blocks = len(self.state.completed_blocks)
        current_block = self.get_current_block()
        
        return {
            "total_blocks": total_blocks,
            "completed_blocks": completed_blocks,
            "current_block_index": self.state.current_block_index,
            "current_block": current_block.title if current_block else None,
            "progress_percent": (completed_blocks / total_blocks * 100) if total_blocks > 0 else 0,
            "is_running": self.state.is_running
        }
    
    def _show_session_summary(self):
        """Show summary of completed session"""
        progress = self.get_progress()
        completed = progress["completed_blocks"]
        total = progress["total_blocks"]
        
        pomodoros_completed = len([
            i for i in self.state.completed_blocks
            if i < len(self.blocks) and self.blocks[i].type == 'pomodoro'
        ])
        
        print(f"\n📊 Session Summary:")
        print(f"   Completed blocks: {completed}/{total}")
        print(f"   Pomodoros completed: {pomodoros_completed}")
        
        if self.state.start_time:
            duration = datetime.now(timezone.utc) - self.state.start_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"   Session duration: {int(hours):02d}:{int(minutes):02d}")


def run_timer(blocks: List[Block], start_index: int = 0, use_tts: bool = False) -> TimerState:
    """Convenience function to run timer with blocks"""
    timer = PomodoroTimer(blocks, use_tts=use_tts)
    timer.start(start_index)
    return timer.state