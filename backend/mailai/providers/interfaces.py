"""Provider interfaces for pluggable components."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime


@dataclass
class MessageMeta:
    """Metadata for a Gmail message."""
    gmail_id: str
    thread_id: str
    date: datetime
    from_email: str
    subject: str
    labels: List[str]
    snippet: str


@dataclass
class Message:
    """Full Gmail message with body."""
    gmail_id: str
    thread_id: str
    date: datetime
    from_email: str
    subject: str
    labels: List[str]
    body: str
    snippet: str
    
    # Recipients and threading  
    to_emails_json: Optional[List[str]] = None
    cc_emails_json: Optional[List[str]] = None
    bcc_emails_json: Optional[List[str]] = None
    reply_to_email: Optional[str] = None
    
    # Message metadata
    message_size: Optional[int] = None
    has_attachments: bool = False
    attachment_count: int = 0
    
    # Message headers for proper threading
    message_id_header: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: Optional[str] = None
    content_type: Optional[str] = None
    is_multipart: bool = False


@dataclass
class ScoredCandidate:
    """Candidate text with ID and optional scores."""
    id: str
    text: str
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Citation:
    """Citation reference."""
    gmail_id: str
    thread_id: str
    date: datetime
    quote: str


@dataclass
class QueryPlan:
    """Planned Gmail query."""
    query_str: str
    rationale: str
    est_hits: int


class GmailProvider(ABC):
    """Interface for Gmail data access."""
    
    @abstractmethod
    async def search(self, query_str: str) -> List[MessageMeta]:
        """
        Search Gmail messages by query string.
        
        Args:
            query_str: Gmail search operators string
            
        Returns:
            List of message metadata
        """
        pass
    
    @abstractmethod
    async def fetch_bodies(self, message_ids: List[str]) -> List[Message]:
        """
        Fetch full message bodies by ID.
        
        Args:
            message_ids: List of Gmail message IDs
            
        Returns:
            List of full messages with bodies
        """
        pass
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with Gmail API.
        
        Returns:
            True if authentication successful
        """
        pass


class EmbedProvider(ABC):
    """Interface for text embeddings."""
    
    @abstractmethod
    async def embed(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for text list.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            Array of embeddings, shape (len(texts), dim)
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier."""
        pass


class RerankProvider(ABC):
    """Interface for reranking candidates."""
    
    @abstractmethod
    async def rerank(
        self, 
        query: str, 
        candidates: List[ScoredCandidate]
    ) -> List[ScoredCandidate]:
        """
        Rerank candidates by relevance to query.
        
        Args:
            query: Query text
            candidates: List of candidates to rerank
            
        Returns:
            Reranked candidates (may be filtered/truncated)
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier."""
        pass


class LLMProvider(ABC):
    """Interface for language model operations."""
    
    @abstractmethod
    async def summarize(
        self, 
        thread_chunks: List[str], 
        topic: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Summarize thread chunks into bullets with citations.
        
        Args:
            thread_chunks: List of text chunks from thread
            topic: Topic/question for summarization
            context: Additional context
            
        Returns:
            Tuple of (summary_markdown, bullets_with_citations)
        """
        pass
    
    @abstractmethod
    async def answer(
        self, 
        question: str, 
        evidence_chunks: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Citation], float]:
        """
        Answer question from evidence chunks.
        
        Args:
            question: User question
            evidence_chunks: Relevant text chunks
            context: Additional context
            
        Returns:
            Tuple of (answer_markdown, citations, confidence)
        """
        pass
    
    @abstractmethod
    async def plan_expansion(
        self, 
        question: str, 
        current_evidence: List[str],
        gaps: List[str]
    ) -> List[QueryPlan]:
        """
        Plan query expansion to fill gaps.
        
        Args:
            question: Original question
            current_evidence: Current evidence chunks
            gaps: Identified gaps in evidence
            
        Returns:
            List of planned queries
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier."""
        pass


class VectorStore(ABC):
    """Interface for vector similarity search."""
    
    @abstractmethod
    async def index(self, vectors: np.ndarray, ids: List[str]) -> None:
        """
        Index vectors with IDs.
        
        Args:
            vectors: Array of vectors, shape (n, dim)
            ids: List of IDs for each vector
        """
        pass
    
    @abstractmethod
    async def search(
        self, 
        query_vector: np.ndarray, 
        top_k: int = 50
    ) -> List[Tuple[str, float]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query vector
            top_k: Number of results to return
            
        Returns:
            List of (id, score) tuples
        """
        pass
    
    @abstractmethod
    async def save(self, path: str) -> None:
        """Save index to disk."""
        pass
    
    @abstractmethod
    async def load(self, path: str) -> None:
        """Load index from disk."""
        pass
    
    @property
    @abstractmethod
    def size(self) -> int:
        """Number of indexed vectors."""
        pass


class BM25Provider(ABC):
    """Interface for BM25 text search."""
    
    @abstractmethod
    async def index(self, texts: List[str], ids: List[str]) -> None:
        """
        Index texts with IDs.
        
        Args:
            texts: List of text strings
            ids: List of IDs for each text
        """
        pass
    
    @abstractmethod
    async def search(
        self, 
        query: str, 
        top_k: int = 100
    ) -> List[Tuple[str, float]]:
        """
        Search texts by BM25 relevance.
        
        Args:
            query: Query string
            top_k: Number of results to return
            
        Returns:
            List of (id, score) tuples
        """
        pass