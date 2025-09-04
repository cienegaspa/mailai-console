"""FastAPI main application with SSE support."""

# Load environment variables FIRST, before any other imports
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    # Look for .env in project root (two levels up from this file)
    env_path = Path(__file__).parent.parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
        print(f"✅ Loaded environment variables from {env_path}")
        print(f"✅ MAILAI_MOCKS = {os.getenv('MAILAI_MOCKS', 'NOT_SET')}")
        client_id = os.getenv('GOOGLE_CLIENT_ID', 'NOT_SET')
        print(f"✅ GOOGLE_CLIENT_ID = {client_id[:20]}..." if client_id != 'NOT_SET' else "✅ GOOGLE_CLIENT_ID = NOT_SET")
    else:
        print(f"⚠️ No .env file found at {env_path}")
except ImportError:
    print("⚠️ python-dotenv not installed - using system environment variables only")

import asyncio
import json
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ..models.simple_db import (
    get_session, init_db, Run, RunCreate, RunResponse, RunStatus,
    Query, QueryResponse, Summary, Message, Chunk, Export
)
from ..core.runner import RunOrchestrator, RunConfig
from ..providers.mock import (
    MockGmailProvider, MockEmbedProvider, MockRerankProvider, 
    MockLLMProvider, MockVectorStore, MockBM25Provider
)
from ..providers.interfaces import (
    GmailProvider, EmbedProvider, RerankProvider,
    LLMProvider, VectorStore, BM25Provider
)
from ..utils.events import global_event_emitter, global_progress_tracker, RunEvent
from .auth import router as auth_router


# Pydantic models for API
class RunCreateRequest(BaseModel):
    question: str
    after: Optional[str] = None
    before: Optional[str] = None
    domains: Optional[List[str]] = None
    max_iters: Optional[int] = 4
    use_api_planner: Optional[bool] = False
    polish_with_api: Optional[bool] = False


class QARequest(BaseModel):
    question: str
    mode: str = "cached"  # cached | auto_expand | plan


class QAResponse(BaseModel):
    qa_id: str
    answer_md: str
    citations: List[Dict[str, Any]]
    confidence: float
    used_expansion: bool = False
    artifacts: Optional[Dict[str, Any]] = None


class ThreadSummary(BaseModel):
    thread_id: str
    first_date: Optional[str]
    last_date: Optional[str] 
    participants: List[str]
    top_score: float
    summary_md: str
    bullets: List[Dict[str, Any]]


class RunDetail(BaseModel):
    run_id: str
    question: str
    params: Dict[str, Any]
    status: str
    eta_ms: Optional[int]
    stop_reason: Optional[str]
    models: Dict[str, str]
    metrics: Optional[Dict[str, Any]]


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting MailAI Console API...")
    
    # Initialize database
    init_db()
    
    # Initialize providers based on configuration
    await initialize_providers()
    
    yield
    
    # Shutdown
    print("Shutting down MailAI Console API...")


# Global provider instances
providers: Dict[str, Any] = {}
orchestrator: Optional[RunOrchestrator] = None


async def initialize_providers():
    """Initialize providers based on configuration."""
    global providers, orchestrator
    
    use_mocks = os.getenv("MAILAI_MOCKS", "true").lower() == "true"
    
    if use_mocks:
        print("Initializing with mock providers...")
        providers = {
            "gmail": MockGmailProvider(),
            "embed": MockEmbedProvider(),
            "rerank": MockRerankProvider(),
            "llm": MockLLMProvider(),
            "vector": MockVectorStore(),
            "bm25": MockBM25Provider()
        }
    else:
        # TODO: Initialize real providers
        print("Real providers not implemented yet, falling back to mocks...")
        providers = {
            "gmail": MockGmailProvider(),
            "embed": MockEmbedProvider(),
            "rerank": MockRerankProvider(),
            "llm": MockLLMProvider(),
            "vector": MockVectorStore(),
            "bm25": MockBM25Provider()
        }
    
    # Initialize orchestrator
    orchestrator = RunOrchestrator(
        gmail_provider=providers["gmail"],
        embed_provider=providers["embed"],
        rerank_provider=providers["rerank"],
        llm_provider=providers["llm"],
        vector_store=providers["vector"],
        bm25_provider=providers["bm25"],
        event_emitter=global_event_emitter
    )


# FastAPI app
app = FastAPI(
    title="MailAI Console API",
    description="Local Gmail Evidence Console for Attorney Questions",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5171", "http://127.0.0.1:5171"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include OAuth router
app.include_router(auth_router)


# Dependency to get orchestrator
def get_orchestrator() -> RunOrchestrator:
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    return orchestrator


# API Routes
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "MailAI Console API",
        "status": "running",
        "version": "1.0.0"
    }


@app.post("/runs", response_model=Dict[str, str])
async def create_run(
    request: RunCreateRequest,
    background_tasks: BackgroundTasks,
    orchestrator: RunOrchestrator = Depends(get_orchestrator)
):
    """Create a new run."""
    config = RunConfig(
        question=request.question,
        after=request.after,
        before=request.before,
        domains=request.domains,
        max_iters=request.max_iters or 4,
        use_api_planner=request.use_api_planner or False,
        polish_with_api=request.polish_with_api or False
    )
    
    run_id = await orchestrator.create_run(config)
    
    # Start execution in background
    background_tasks.add_task(orchestrator.execute_run, run_id)
    
    return {"run_id": run_id}


@app.get("/runs", response_model=List[RunResponse])
async def list_runs():
    """List all runs."""
    session = get_session()
    try:
        runs = session.query(Run).order_by(Run.created_at.desc()).all()
        return [
            RunResponse(
                run_id=run.run_id,
                created_at=run.created_at,
                question=run.question,
                status=run.status,
                metrics=run.metrics_json,
                eta_ms=run.eta_ms
            )
            for run in runs
        ]
    finally:
        session.close()


@app.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(run_id: str):
    """Get run details."""
    session = get_session()
    try:
        run = session.query(Run).filter(Run.run_id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        return RunDetail(
            run_id=run.run_id,
            question=run.question,
            params=run.params_json or {},
            status=run.status,
            eta_ms=run.eta_ms,
            stop_reason=run.stop_reason,
            models=run.models_json or {},
            metrics=run.metrics_json or {}
        )
    finally:
        session.close()


@app.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str):
    """Stream run events via SSE."""
    async def event_generator():
        queue = global_event_emitter.get_run_queue(run_id)
        
        while True:
            try:
                # Wait for next event with timeout
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                
                # Check if run is complete
                if event.type in [RunEvent.RUN_COMPLETE, RunEvent.RUN_FAILED, RunEvent.RUN_CANCELLED]:
                    yield {
                        "event": event.type.value,
                        "data": event.to_json()
                    }
                    break
                
                yield {
                    "event": event.type.value, 
                    "data": event.to_json()
                }
                
            except asyncio.TimeoutError:
                # Send keepalive
                yield {
                    "event": "keepalive",
                    "data": json.dumps({"timestamp": event.timestamp.isoformat()})
                }
            except Exception as e:
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }
                break
    
    return EventSourceResponse(event_generator())


@app.get("/runs/{run_id}/queries", response_model=List[QueryResponse])
async def get_run_queries(run_id: str):
    """Get queries executed for a run."""
    session = get_session()
    try:
        queries = session.query(Query).filter(
            Query.run_id == run_id
        ).order_by(Query.iteration, Query.id).all()
        
        return [
            QueryResponse(
                iteration=q.iteration,
                query_str=q.query_str,
                rationale=q.rationale,
                hits=q.hits,
                new_msgs=q.new_msgs,
                new_threads=q.new_threads,
                exec_ms=q.exec_ms
            )
            for q in queries
        ]
    finally:
        session.close()


@app.get("/runs/{run_id}/terms")
async def get_run_terms(run_id: str):
    """Get term expansions for a run."""
    session = get_session()
    try:
        from ..models.simple_db import TermExpansion
        
        terms = session.query(TermExpansion).filter(
            TermExpansion.run_id == run_id
        ).order_by(TermExpansion.iteration).all()
        
        return [
            {
                "iteration": t.iteration,
                "added_terms": t.added_terms_json or [],
                "removed_terms": t.removed_terms_json or [],
                "evidence_terms": t.evidence_terms_json or []
            }
            for t in terms
        ]
    finally:
        session.close()


@app.get("/runs/{run_id}/threads", response_model=List[ThreadSummary])
async def get_run_threads(run_id: str):
    """Get thread summaries for a run."""
    session = get_session()
    try:
        from ..models.simple_db import Thread
        
        threads = session.query(Thread).filter(
            Thread.run_id == run_id
        ).order_by(Thread.top_score.desc()).all()
        
        # Get summaries for threads
        summaries = session.query(Summary).filter(
            Summary.run_id == run_id
        ).all()
        
        summary_lookup = {s.thread_id: s for s in summaries}
        
        result = []
        for thread in threads:
            summary = summary_lookup.get(thread.thread_id)
            result.append(ThreadSummary(
                thread_id=thread.thread_id,
                first_date=thread.first_date.isoformat() if thread.first_date else None,
                last_date=thread.last_date.isoformat() if thread.last_date else None,
                participants=thread.participants_json or [],
                top_score=thread.top_score or 0.0,
                summary_md=summary.summary_md if summary else "",
                bullets=summary.bullets_json if summary else []
            ))
        
        return result
    finally:
        session.close()


@app.get("/runs/{run_id}/messages")
async def get_run_messages(run_id: str, thread_id: Optional[str] = None):
    """Get messages for a run, optionally filtered by thread."""
    session = get_session()
    try:
        query = session.query(Message).filter(Message.run_id == run_id)
        
        if thread_id:
            query = query.filter(Message.thread_id == thread_id)
        
        messages = query.order_by(Message.date).all()
        
        return [
            {
                "gmail_id": m.gmail_id,
                "thread_id": m.thread_id,
                "date": m.date.isoformat(),
                "from_email": m.from_email,
                "subject": m.subject,
                "labels": m.labels_json or [],
                "snippet": m.snippet
            }
            for m in messages
        ]
    finally:
        session.close()


@app.post("/runs/{run_id}/qa", response_model=Dict[str, str])
async def create_qa(
    run_id: str,
    request: QARequest,
    background_tasks: BackgroundTasks,
    orchestrator: RunOrchestrator = Depends(get_orchestrator)
):
    """Create Q&A interaction for a run."""
    from datetime import datetime
    from ..models.simple_db import RunMessage, MessageRole
    
    session = get_session()
    try:
        # Save user question
        user_message = RunMessage(
            run_id=run_id,
            role=MessageRole.USER,
            text=request.question,
            created_at=datetime.utcnow(),
            mode=request.mode,
            used_expansion=False
        )
        session.add(user_message)
        session.commit()
        
        # Generate mock AI response for demo
        import random
        responses = [
            "Based on the existing evidence from the CoolSculpting Elite analysis, I can see several patterns related to your question. Let me search for additional relevant information.",
            "Looking at the processed messages and threads, here's what I found regarding your follow-up question. The data shows connections to the original device return issues.",
            "Your question relates to several aspects covered in the initial analysis. I've identified additional relevant threads that help answer this inquiry.",
            "This follow-up connects well with the CoolSculpting Elite case data. I can provide more specific details based on the evidence already collected."
        ]
        
        ai_response = random.choice(responses)
        
        # Save AI response
        ai_message = RunMessage(
            run_id=run_id,
            role=MessageRole.ASSISTANT,
            text=ai_response,
            created_at=datetime.utcnow(),
            mode="cached",
            used_expansion=False,
            artifacts_json={"confidence": 0.85, "sources": ["mock_thread_1", "mock_thread_2"]}
        )
        session.add(ai_message)
        session.commit()
        
        qa_id = str(ai_message.id)
        return {"qa_id": qa_id}
        
    finally:
        session.close()


@app.get("/runs/{run_id}/qa")
async def get_run_qa(run_id: str):
    """Get Q&A history for a run."""
    session = get_session()
    try:
        from ..models.simple_db import RunMessage
        
        messages = session.query(RunMessage).filter(
            RunMessage.run_id == run_id
        ).order_by(RunMessage.created_at).all()
        
        return [
            {
                "qa_id": str(m.id),
                "role": m.role,
                "text": m.text,
                "created_at": m.created_at.isoformat(),
                "mode": m.mode,
                "used_expansion": m.used_expansion,
                "artifacts": m.artifacts_json
            }
            for m in messages
        ]
    finally:
        session.close()


@app.post("/runs/{run_id}/export")
async def create_export(run_id: str):
    """Create export artifacts for a run."""
    # TODO: Implement export functionality
    export_paths = {
        "pdf_path": f"./exports/{run_id}_packet.pdf",
        "csv_path": f"./exports/{run_id}_hits.csv", 
        "log_path": f"./exports/{run_id}_log.json"
    }
    
    return export_paths


# Control endpoints
@app.post("/runs/{run_id}/pause")
async def pause_run(
    run_id: str,
    orchestrator: RunOrchestrator = Depends(get_orchestrator)
):
    """Pause a running run."""
    await orchestrator.pause_run(run_id)
    return {"status": "paused"}


@app.post("/runs/{run_id}/resume")
async def resume_run(
    run_id: str,
    orchestrator: RunOrchestrator = Depends(get_orchestrator)
):
    """Resume a paused run."""
    await orchestrator.resume_run(run_id)
    return {"status": "resumed"}


@app.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    orchestrator: RunOrchestrator = Depends(get_orchestrator)
):
    """Cancel a running run."""
    await orchestrator.cancel_run(run_id)
    return {"status": "cancelled"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5170)