"""Event system for real-time updates during runs."""

import asyncio
import json
from enum import Enum
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime


class RunEvent(str, Enum):
    """Types of run events."""
    RUN_STARTED = "run_started"
    RUN_COMPLETE = "run_complete"
    RUN_FAILED = "run_failed"
    RUN_PAUSED = "run_paused"
    RUN_RESUMED = "run_resumed"
    RUN_CANCELLED = "run_cancelled"
    
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETE = "phase_complete"
    PHASE_PROGRESS = "phase_progress"
    
    ITERATION_STARTED = "iteration_started"
    ITERATION_COMPLETE = "iteration_complete"
    
    QUERY_EXECUTED = "query_executed"
    MESSAGES_FETCHED = "messages_fetched"
    CHUNKS_PROCESSED = "chunks_processed"
    RANKING_COMPLETE = "ranking_complete"
    SUMMARY_GENERATED = "summary_generated"
    
    ERROR_OCCURRED = "error_occurred"
    WARNING_ISSUED = "warning_issued"


@dataclass
class Event:
    """Event data structure."""
    type: RunEvent
    run_id: str
    timestamp: datetime
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


class EventEmitter:
    """Event emitter for real-time run updates."""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._run_queues: Dict[str, asyncio.Queue] = {}
        self._global_queue: asyncio.Queue = asyncio.Queue()
    
    def subscribe(self, event_type: RunEvent, callback: Callable[[Event], None]) -> None:
        """Subscribe to specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def unsubscribe(self, event_type: RunEvent, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from event type."""
        if event_type in self._listeners:
            self._listeners[event_type] = [
                cb for cb in self._listeners[event_type] if cb != callback
            ]
    
    async def emit(self, event_type: RunEvent, data: Dict[str, Any]) -> None:
        """Emit an event to all subscribers."""
        run_id = data.get("run_id", "unknown")
        
        event = Event(
            type=event_type,
            run_id=run_id,
            timestamp=datetime.utcnow(),
            data=data
        )
        
        # Call registered callbacks
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    print(f"Error in event callback: {e}")
        
        # Add to run-specific queue
        if run_id not in self._run_queues:
            self._run_queues[run_id] = asyncio.Queue()
        
        await self._run_queues[run_id].put(event)
        
        # Add to global queue for SSE
        await self._global_queue.put(event)
    
    def get_run_queue(self, run_id: str) -> asyncio.Queue:
        """Get event queue for specific run."""
        if run_id not in self._run_queues:
            self._run_queues[run_id] = asyncio.Queue()
        return self._run_queues[run_id]
    
    def get_global_queue(self) -> asyncio.Queue:
        """Get global event queue for SSE streaming."""
        return self._global_queue
    
    async def get_run_events(self, run_id: str) -> List[Event]:
        """Get all events for a run (non-blocking)."""
        events = []
        if run_id in self._run_queues:
            queue = self._run_queues[run_id]
            while not queue.empty():
                try:
                    event = queue.get_nowait()
                    events.append(event)
                except asyncio.QueueEmpty:
                    break
        return events
    
    async def wait_for_run_event(
        self, 
        run_id: str, 
        event_types: List[RunEvent],
        timeout: float = 30.0
    ) -> Optional[Event]:
        """Wait for specific event types for a run."""
        queue = self.get_run_queue(run_id)
        
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=timeout)
                if event.type in event_types:
                    return event
                # Put back events we don't want
                await queue.put(event)
        except asyncio.TimeoutError:
            return None
    
    def clear_run_events(self, run_id: str) -> None:
        """Clear all events for a run."""
        if run_id in self._run_queues:
            # Create new queue to clear old events
            self._run_queues[run_id] = asyncio.Queue()


class ProgressTracker:
    """Progress tracking for runs with ETA estimation."""
    
    def __init__(self, event_emitter: EventEmitter):
        self.events = event_emitter
        self._run_progress: Dict[str, Dict[str, Any]] = {}
    
    async def start_run(self, run_id: str, total_phases: int = 6) -> None:
        """Start tracking progress for a run."""
        self._run_progress[run_id] = {
            "total_phases": total_phases,
            "current_phase": 0,
            "phase_progress": 0.0,
            "started_at": datetime.utcnow(),
            "estimated_duration_ms": None,
            "phases": [
                {"name": "Fetching", "weight": 0.4},
                {"name": "Normalizing", "weight": 0.1}, 
                {"name": "Ranking", "weight": 0.2},
                {"name": "Iterating", "weight": 0.1},
                {"name": "Summarizing", "weight": 0.1},
                {"name": "Exporting", "weight": 0.1}
            ]
        }
        
        await self.events.emit(RunEvent.PHASE_PROGRESS, {
            "run_id": run_id,
            "overall_progress": 0.0,
            "current_phase": "Starting",
            "eta_ms": None
        })
    
    async def start_phase(self, run_id: str, phase_name: str, phase_index: int) -> None:
        """Start a new phase."""
        if run_id not in self._run_progress:
            return
        
        progress = self._run_progress[run_id]
        progress["current_phase"] = phase_index
        progress["phase_progress"] = 0.0
        
        overall_progress = self._calculate_overall_progress(run_id)
        eta_ms = self._estimate_eta(run_id)
        
        await self.events.emit(RunEvent.PHASE_STARTED, {
            "run_id": run_id,
            "phase": phase_name,
            "phase_index": phase_index,
            "overall_progress": overall_progress,
            "eta_ms": eta_ms
        })
    
    async def update_phase_progress(
        self, 
        run_id: str, 
        phase_progress: float,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update progress within current phase."""
        if run_id not in self._run_progress:
            return
        
        progress = self._run_progress[run_id]
        progress["phase_progress"] = min(phase_progress, 1.0)
        
        overall_progress = self._calculate_overall_progress(run_id)
        eta_ms = self._estimate_eta(run_id)
        
        await self.events.emit(RunEvent.PHASE_PROGRESS, {
            "run_id": run_id,
            "phase_progress": phase_progress,
            "overall_progress": overall_progress,
            "eta_ms": eta_ms,
            "details": details or {}
        })
    
    async def complete_phase(self, run_id: str, phase_name: str) -> None:
        """Mark phase as complete."""
        if run_id not in self._run_progress:
            return
        
        progress = self._run_progress[run_id]
        progress["phase_progress"] = 1.0
        
        overall_progress = self._calculate_overall_progress(run_id)
        
        await self.events.emit(RunEvent.PHASE_COMPLETE, {
            "run_id": run_id,
            "phase": phase_name,
            "overall_progress": overall_progress
        })
    
    async def complete_run(self, run_id: str) -> None:
        """Mark run as complete."""
        if run_id not in self._run_progress:
            return
        
        progress = self._run_progress[run_id]
        completed_at = datetime.utcnow()
        duration = (completed_at - progress["started_at"]).total_seconds() * 1000
        
        await self.events.emit(RunEvent.PHASE_PROGRESS, {
            "run_id": run_id,
            "overall_progress": 1.0,
            "phase_progress": 1.0,
            "current_phase": "Complete",
            "duration_ms": int(duration),
            "eta_ms": 0
        })
        
        # Clean up
        del self._run_progress[run_id]
    
    def _calculate_overall_progress(self, run_id: str) -> float:
        """Calculate overall progress percentage."""
        progress = self._run_progress[run_id]
        current_phase = progress["current_phase"]
        phase_progress = progress["phase_progress"]
        phases = progress["phases"]
        
        # Calculate progress based on weighted phases
        total_weight = 0.0
        completed_weight = 0.0
        
        for i, phase in enumerate(phases):
            weight = phase["weight"]
            total_weight += weight
            
            if i < current_phase:
                # Completed phases
                completed_weight += weight
            elif i == current_phase:
                # Current phase
                completed_weight += weight * phase_progress
        
        return completed_weight / total_weight if total_weight > 0 else 0.0
    
    def _estimate_eta(self, run_id: str) -> Optional[int]:
        """Estimate time remaining in milliseconds."""
        progress = self._run_progress[run_id]
        started_at = progress["started_at"]
        overall_progress = self._calculate_overall_progress(run_id)
        
        if overall_progress <= 0:
            return None
        
        elapsed_ms = (datetime.utcnow() - started_at).total_seconds() * 1000
        
        if overall_progress < 0.05:  # Less than 5% complete
            return None
        
        # Estimate total time and subtract elapsed time
        estimated_total_ms = elapsed_ms / overall_progress
        remaining_ms = estimated_total_ms - elapsed_ms
        
        return max(int(remaining_ms), 0)


# Global event emitter instance
global_event_emitter = EventEmitter()
global_progress_tracker = ProgressTracker(global_event_emitter)