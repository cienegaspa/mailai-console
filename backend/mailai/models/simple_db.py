"""Simplified database models for MailAI Console that actually work."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    JSON,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import os

Base = declarative_base()


class GmailAccount(Base):
    """Gmail account with OAuth tokens."""
    __tablename__ = "gmail_accounts"
    
    account_id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String)
    
    # OAuth tokens
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    
    # Status and metadata
    status = Column(String, default="disconnected")  # connected, disconnected, error, pending
    connected_at = Column(DateTime)
    last_sync = Column(DateTime)
    sync_error = Column(Text)
    
    # Stats
    total_messages = Column(Integer, default=0)
    last_message_date = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Index for faster lookups
    __table_args__ = (
        Index('idx_gmail_accounts_email', 'email'),
        Index('idx_gmail_accounts_status', 'status'),
    )


class RunStatus(str, Enum):
    """Status of a run."""
    QUEUED = "queued"
    FETCHING = "fetching"
    NORMALIZING = "normalizing"
    RANKING = "ranking"
    ITERATING = "iterating"
    SUMMARIZING = "summarizing"
    EXPORTING = "exporting"
    DONE = "done"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class MessageRole(str, Enum):
    """Role of a message in a conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Run(Base):
    """Primary run table."""
    __tablename__ = "runs"
    
    run_id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    question = Column(Text, nullable=False)
    params_json = Column(JSON)
    status = Column(String, default=RunStatus.QUEUED)
    eta_ms = Column(Integer)
    stop_reason = Column(String)
    models_json = Column(JSON)
    metrics_json = Column(JSON)


class RunMessage(Base):
    """Messages in a run conversation."""
    __tablename__ = "run_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    role = Column(String, nullable=False)  # MessageRole
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    mode = Column(String)  # MessageMode
    used_expansion = Column(Boolean, default=False)
    artifacts_json = Column(JSON)


class Query(Base):
    """Gmail queries executed during runs."""
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    iteration = Column(Integer, nullable=False)
    query_str = Column(Text, nullable=False)
    rationale = Column(Text)
    hits = Column(Integer, default=0)
    new_msgs = Column(Integer, default=0)
    new_threads = Column(Integer, default=0)
    exec_ms = Column(Integer)
    
    # Indexes
    __table_args__ = (
        Index("idx_query_run_iteration", "run_id", "iteration"),
    )


class TermExpansion(Base):
    """Term expansion tracking per iteration."""
    __tablename__ = "terms"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    iteration = Column(Integer, nullable=False)
    added_terms_json = Column(JSON)
    removed_terms_json = Column(JSON)
    evidence_terms_json = Column(JSON)
    
    # Indexes
    __table_args__ = (
        Index("idx_terms_run_iteration", "run_id", "iteration"),
    )


class Message(Base):
    """Messages associated with specific runs."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    gmail_id = Column(String, nullable=False)
    thread_id = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    from_email = Column(String, nullable=False)
    subject = Column(String)
    labels_json = Column(JSON)
    snippet = Column(Text)
    selected = Column(Boolean, default=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_run_message_date", "run_id", "date"),
        Index("idx_run_message_from", "run_id", "from_email"),
    )


class Chunk(Base):
    """Text chunks for a specific run."""
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    chunk_id = Column(String, nullable=False)
    gmail_id = Column(String, nullable=False)
    idx = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    token_count = Column(Integer)
    bm25_score = Column(Float)
    knn_score = Column(Float)
    rerank_score = Column(Float)
    selected = Column(Boolean, default=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_chunk_run_gmail", "run_id", "gmail_id"),
        Index("idx_chunk_rerank", "rerank_score"),
    )


class Thread(Base):
    """Thread summaries for runs."""
    __tablename__ = "threads"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    thread_id = Column(String, nullable=False)
    first_date = Column(DateTime)
    last_date = Column(DateTime)
    participants_json = Column(JSON)
    top_score = Column(Float)
    selected = Column(Boolean, default=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_thread_run_score", "run_id", "top_score"),
    )


class Summary(Base):
    """Thread summaries."""
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    thread_id = Column(String, nullable=False)
    summary_md = Column(Text)
    bullets_json = Column(JSON)  # List of bullets with quotes and citations
    confidence = Column(Float)


class Export(Base):
    """Export artifacts."""
    __tablename__ = "exports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, nullable=False)
    pdf_path = Column(String)
    csv_path = Column(String)
    log_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database initialization
def get_database_url() -> str:
    """Get database URL from environment."""
    db_path = os.getenv("MAILAI_DB_PATH", "./db/mailai.sqlite")
    return f"sqlite:///{db_path}"


def create_engine_and_session():
    """Create SQLAlchemy engine and session."""
    engine = create_engine(
        get_database_url(),
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal


def init_db():
    """Initialize database with all tables."""
    engine, _ = create_engine_and_session()
    
    # Ensure directory exists
    db_path = os.getenv("MAILAI_DB_PATH", "./db/mailai.sqlite")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at {db_path}")


def get_session() -> Session:
    """Get database session."""
    _, SessionLocal = create_engine_and_session()
    return SessionLocal()


# Pydantic models for API
class RunCreate(BaseModel):
    question: str
    after: Optional[str] = None
    before: Optional[str] = None
    domains: Optional[List[str]] = None
    max_iters: Optional[int] = 4
    use_api_planner: Optional[bool] = False
    polish_with_api: Optional[bool] = False


class RunResponse(BaseModel):
    run_id: str
    created_at: datetime
    question: str
    status: str
    metrics: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None
    eta_ms: Optional[int] = None

    class Config:
        from_attributes = True


class QueryResponse(BaseModel):
    iteration: int
    query_str: str
    rationale: Optional[str]
    hits: int
    new_msgs: int
    new_threads: int
    exec_ms: Optional[int]

    class Config:
        from_attributes = True