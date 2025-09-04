"""Core task runner and orchestrator for MailAI Console."""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from ..models.simple_db import (
    get_session, Run, RunStatus, Query, TermExpansion, Message, Chunk, 
    Thread, Summary, RunCreate
)
from ..providers.interfaces import (
    GmailProvider, EmbedProvider, RerankProvider, LLMProvider, 
    VectorStore, BM25Provider, ScoredCandidate
)
from ..utils.text_processing import TextProcessor
from ..utils.events import EventEmitter, RunEvent


@dataclass 
class RunConfig:
    """Configuration for a run."""
    question: str
    after: Optional[str] = None
    before: Optional[str] = None  
    domains: Optional[List[str]] = None
    max_iters: int = 4
    use_api_planner: bool = False
    polish_with_api: bool = False
    min_precision: float = 0.3
    min_novelty_gain: float = 0.02
    max_chunks_per_iter: int = 100
    chunk_size: int = 800
    chunk_overlap: int = 100


@dataclass
class IterationMetrics:
    """Metrics for a single iteration."""
    iteration: int
    queries_tried: int
    new_messages: int
    new_threads: int
    total_chunks: int
    precision_proxy: float
    novelty_gain: float
    duration_ms: int
    stop_reason: Optional[str] = None


class RunOrchestrator:
    """Main orchestrator for Gmail retrieval and analysis runs."""
    
    def __init__(
        self,
        gmail_provider: GmailProvider,
        embed_provider: EmbedProvider,
        rerank_provider: RerankProvider,
        llm_provider: LLMProvider,
        vector_store: VectorStore,
        bm25_provider: BM25Provider,
        event_emitter: EventEmitter
    ):
        self.gmail = gmail_provider
        self.embed = embed_provider
        self.rerank = rerank_provider
        self.llm = llm_provider
        self.vector_store = vector_store
        self.bm25 = bm25_provider
        self.events = event_emitter
        self.text_processor = TextProcessor()
        
        # State tracking
        self.current_run: Optional[str] = None
        self.should_stop = False
        self.is_paused = False
    
    async def create_run(self, config: RunConfig) -> str:
        """Create a new run and return run ID."""
        run_id = f"{datetime.now().strftime('%Y-%m-%d')}-{str(uuid.uuid4())[:8]}"
        
        # Store in database
        session = get_session()
        try:
            run = Run(
                run_id=run_id,
                question=config.question,
                params_json={
                    "after": config.after,
                    "before": config.before,
                    "domains": config.domains,
                    "max_iters": config.max_iters,
                    "use_api_planner": config.use_api_planner,
                    "polish_with_api": config.polish_with_api
                },
                status=RunStatus.QUEUED,
                models_json={
                    "embed": self.embed.model_name,
                    "rerank": self.rerank.model_name,
                    "llm": self.llm.model_name
                }
            )
            session.add(run)
            session.commit()
        finally:
            session.close()
        
        return run_id
    
    async def execute_run(self, run_id: str) -> None:
        """Execute a complete run."""
        self.current_run = run_id
        self.should_stop = False
        
        session = get_session()
        try:
            run = session.query(Run).filter(Run.run_id == run_id).first()
            if not run:
                raise ValueError(f"Run {run_id} not found")
            
            config = RunConfig(
                question=run.question,
                **run.params_json
            )
            
            await self._execute_run_phases(run_id, config)
            
        except Exception as e:
            await self._update_run_status(run_id, RunStatus.FAILED, str(e))
            raise
        finally:
            session.close()
    
    async def _execute_run_phases(self, run_id: str, config: RunConfig) -> None:
        """Execute all phases of a run."""
        start_time = time.time()
        
        try:
            # Phase 1: Initialize
            await self._update_run_status(run_id, RunStatus.FETCHING)
            await self.events.emit(RunEvent.PHASE_STARTED, {
                "run_id": run_id, 
                "phase": "fetching",
                "message": "Starting Gmail search and retrieval"
            })
            
            # Phase 2: Iterative retrieval
            metrics = await self._iterative_retrieval(run_id, config)
            
            if self.should_stop:
                await self._update_run_status(run_id, RunStatus.CANCELLED)
                return
            
            # Phase 3: Normalization and chunking
            await self._update_run_status(run_id, RunStatus.NORMALIZING)
            await self._normalize_and_chunk(run_id)
            
            # Phase 4: Ranking
            await self._update_run_status(run_id, RunStatus.RANKING)
            await self._hybrid_ranking(run_id, config.question)
            
            # Phase 5: Summarization  
            await self._update_run_status(run_id, RunStatus.SUMMARIZING)
            await self._generate_summaries(run_id, config.question)
            
            # Phase 6: Export preparation
            await self._update_run_status(run_id, RunStatus.EXPORTING)
            await self._prepare_exports(run_id)
            
            # Complete
            duration_ms = int((time.time() - start_time) * 1000)
            await self._finalize_run(run_id, metrics, duration_ms)
            
        except Exception as e:
            await self._update_run_status(run_id, RunStatus.FAILED, str(e))
            raise
    
    async def _iterative_retrieval(
        self, 
        run_id: str, 
        config: RunConfig
    ) -> List[IterationMetrics]:
        """Execute iterative Gmail retrieval with term expansion."""
        metrics = []
        seen_messages: Set[str] = set()
        seen_threads: Set[str] = set()
        current_terms = self._extract_initial_terms(config.question)
        
        for iteration in range(config.max_iters):
            if self.should_stop or self.is_paused:
                break
                
            iter_start = time.time()
            
            # Generate queries for this iteration
            queries = await self._generate_queries(
                config.question, 
                current_terms, 
                iteration,
                config
            )
            
            # Execute searches
            iteration_messages = []
            queries_tried = 0
            
            for query_plan in queries:
                if self.should_stop:
                    break
                    
                try:
                    # Search Gmail
                    message_metas = await self.gmail.search(query_plan.query_str)
                    new_messages = [m for m in message_metas if m.gmail_id not in seen_messages]
                    
                    # Fetch full bodies
                    if new_messages:
                        full_messages = await self.gmail.fetch_bodies([m.gmail_id for m in new_messages])
                        iteration_messages.extend(full_messages)
                    
                    # Store query
                    await self._store_query(
                        run_id, 
                        iteration, 
                        query_plan.query_str,
                        query_plan.rationale,
                        len(message_metas),
                        len(new_messages),
                        len(set(m.thread_id for m in new_messages))
                    )
                    
                    queries_tried += 1
                    
                except Exception as e:
                    print(f"Query failed: {query_plan.query_str}, Error: {e}")
                    continue
            
            # Process iteration results
            new_msg_ids = set(m.gmail_id for m in iteration_messages) - seen_messages
            new_thread_ids = set(m.thread_id for m in iteration_messages) - seen_threads
            
            # Update seen sets
            seen_messages.update(new_msg_ids)
            seen_threads.update(new_thread_ids)
            
            # Store messages in database
            await self._store_messages(run_id, iteration_messages)
            
            # Calculate metrics
            precision_proxy = await self._calculate_precision_proxy(
                run_id, 
                config.question,
                iteration_messages
            )
            
            novelty_gain = len(new_thread_ids) / max(len(seen_threads), 1)
            
            duration_ms = int((time.time() - iter_start) * 1000)
            
            iter_metrics = IterationMetrics(
                iteration=iteration,
                queries_tried=queries_tried,
                new_messages=len(new_msg_ids),
                new_threads=len(new_thread_ids),
                total_chunks=0,  # Will be calculated later
                precision_proxy=precision_proxy,
                novelty_gain=novelty_gain,
                duration_ms=duration_ms
            )
            
            metrics.append(iter_metrics)
            
            # Emit progress event
            await self.events.emit(RunEvent.ITERATION_COMPLETE, {
                "run_id": run_id,
                "iteration": iteration,
                "metrics": iter_metrics.__dict__
            })
            
            # Check stopping conditions
            if iteration >= 1:  # Need at least 2 iterations for comparison
                should_stop, reason = await self._check_stopping_conditions(
                    metrics, 
                    config
                )
                if should_stop:
                    iter_metrics.stop_reason = reason
                    break
            
            # Term expansion for next iteration
            if iteration < config.max_iters - 1:
                expanded_terms = await self._expand_terms(
                    run_id,
                    iteration_messages, 
                    current_terms,
                    config.question
                )
                
                await self._store_term_expansion(
                    run_id,
                    iteration + 1, 
                    expanded_terms,
                    current_terms
                )
                
                current_terms = expanded_terms
        
        return metrics
    
    async def _generate_queries(
        self,
        question: str,
        terms: List[str], 
        iteration: int,
        config: RunConfig
    ) -> List:
        """Generate Gmail search queries for iteration."""
        if iteration == 0:
            # Initial seed queries
            queries = await self._generate_seed_queries(question, config)
        else:
            # Expanded queries based on learned terms
            queries = await self._generate_expanded_queries(question, terms, config)
        
        return [type('obj', (object,), {
            'query_str': q,
            'rationale': f"Iteration {iteration} query",
            'est_hits': 0
        }) for q in queries]
    
    async def _generate_seed_queries(
        self, 
        question: str, 
        config: RunConfig
    ) -> List[str]:
        """Generate initial seed queries."""
        # Extract key terms from question
        key_terms = self._extract_initial_terms(question)
        
        queries = []
        
        # Build base constraints
        constraints = []
        if config.after:
            constraints.append(f"after:{config.after}")
        if config.before:  
            constraints.append(f"before:{config.before}")
        if config.domains:
            domain_filter = " OR ".join([f"from:{domain}" for domain in config.domains])
            constraints.append(f"({domain_filter})")
        
        constraint_str = " ".join(constraints)
        
        # Query patterns for CoolSculpting Elite returns
        patterns = [
            f'("return" OR "RMA" OR "ship back" OR "pickup" OR "return label") ("CoolSculpting Elite")',
            f'("CoolSculpting" AND "Elite") AND ("thermal" OR "sensor" OR "E-47" OR "error")', 
            f'("packaging" OR "crate" OR "freight" OR "LTL") ("CoolSculpting")',
            f'("credit" OR "refund" OR "credit memo") ("CoolSculpting Elite")',
            f'("P3" OR "protocol") AND ("CoolSculpting")'
        ]
        
        for pattern in patterns:
            full_query = f"{pattern} {constraint_str}".strip()
            queries.append(full_query)
        
        return queries
    
    async def _generate_expanded_queries(
        self,
        question: str,
        terms: List[str],
        config: RunConfig  
    ) -> List[str]:
        """Generate expanded queries based on learned terms."""
        # Build constraint string
        constraints = []
        if config.after:
            constraints.append(f"after:{config.after}")
        if config.before:
            constraints.append(f"before:{config.before}")
        if config.domains:
            domain_filter = " OR ".join([f"from:{domain}" for domain in config.domains])
            constraints.append(f"({domain_filter})")
        
        constraint_str = " ".join(constraints)
        
        queries = []
        
        # Group terms by category
        logistics_terms = [t for t in terms if any(word in t.lower() for word in 
                          ['ship', 'freight', 'label', 'pickup', 'crate', 'ltl'])]
        error_terms = [t for t in terms if any(word in t.lower() for word in 
                      ['error', 'e-47', 'thermal', 'sensor', 'p3'])]
        process_terms = [t for t in terms if any(word in t.lower() for word in 
                        ['rma', 'return', 'credit', 'refund'])]
        
        # Generate targeted queries
        if logistics_terms:
            quoted_terms = [f'"{term}"' for term in logistics_terms[:3]]
            logistics_query = f'({" OR ".join(quoted_terms)}) {constraint_str}'
            queries.append(logistics_query.strip())
        
        if error_terms:
            quoted_terms = [f'"{term}"' for term in error_terms[:3]]
            error_query = f'({" OR ".join(quoted_terms)}) {constraint_str}'
            queries.append(error_query.strip())
        
        if process_terms:
            quoted_terms = [f'"{term}"' for term in process_terms[:3]]
            process_query = f'({" OR ".join(quoted_terms)}) {constraint_str}'
            queries.append(process_query.strip())
        
        return queries[:3]  # Limit to 3 queries per iteration
    
    def _extract_initial_terms(self, question: str) -> List[str]:
        """Extract initial search terms from question."""
        # Simple keyword extraction - in real implementation would be more sophisticated
        terms = ['CoolSculpting', 'Elite', 'return', 'RMA', 'thermal', 'sensor']
        
        # Add terms from question
        question_words = question.lower().split()
        for word in question_words:
            if len(word) > 3 and word not in ['show', 'what', 'when', 'where', 'how']:
                terms.append(word.title())
        
        return list(set(terms))
    
    async def _expand_terms(
        self,
        run_id: str,
        messages: List,
        current_terms: List[str], 
        question: str
    ) -> List[str]:
        """Expand terms based on co-occurrence in messages."""
        expanded = set(current_terms)
        
        # Extract co-occurring terms from message bodies
        all_text = " ".join([msg.body for msg in messages])
        
        # Simple co-occurrence extraction
        words = all_text.lower().split()
        
        # Look for logistics terms
        logistics_keywords = [
            'waybill', 'bill of lading', 'palletize', 'freight', 'ltl',
            'pickup', 'carrier', 'logistics', 'shipping', 'label'
        ]
        
        # Look for technical terms  
        tech_keywords = [
            'thermal sensor', 'error code', 'manufacturing defect',
            'protocol', 'bypass', 'temperature regulation'
        ]
        
        # Look for process terms
        process_keywords = [
            'credit memo', 'restocking fee', 'inspection', 'warranty',
            'replacement', 'manufacturing year'
        ]
        
        all_keywords = logistics_keywords + tech_keywords + process_keywords
        
        for keyword in all_keywords:
            if keyword in all_text.lower():
                expanded.add(keyword.title())
        
        # Also add sender domains if they appear frequently
        sender_domains = [msg.from_email.split('@')[1] for msg in messages]
        common_domains = set([d for d in sender_domains if sender_domains.count(d) > 1])
        expanded.update(common_domains)
        
        return list(expanded)
    
    async def _store_query(
        self,
        run_id: str,
        iteration: int, 
        query_str: str,
        rationale: str,
        hits: int,
        new_msgs: int,
        new_threads: int
    ) -> None:
        """Store query in database."""
        session = get_session()
        try:
            query = Query(
                run_id=run_id,
                iteration=iteration,
                query_str=query_str,
                rationale=rationale,
                hits=hits,
                new_msgs=new_msgs,
                new_threads=new_threads,
                exec_ms=0  # Could track execution time
            )
            session.add(query)
            session.commit()
        finally:
            session.close()
    
    async def _store_term_expansion(
        self,
        run_id: str,
        iteration: int,
        new_terms: List[str],
        old_terms: List[str]
    ) -> None:
        """Store term expansion in database."""
        session = get_session()
        try:
            added = list(set(new_terms) - set(old_terms))
            removed = list(set(old_terms) - set(new_terms))
            
            expansion = TermExpansion(
                run_id=run_id,
                iteration=iteration,
                added_terms_json=added,
                removed_terms_json=removed, 
                evidence_terms_json=new_terms
            )
            session.add(expansion)
            session.commit()
        finally:
            session.close()
    
    async def _store_messages(self, run_id: str, messages: List) -> None:
        """Store messages in database."""
        session = get_session()
        try:
            for msg in messages:
                message = Message(
                    run_id=run_id,
                    gmail_id=msg.gmail_id,
                    thread_id=msg.thread_id, 
                    date=msg.date,
                    from_email=msg.from_email,
                    subject=msg.subject,
                    labels_json=msg.labels,
                    snippet=msg.snippet
                )
                session.add(message)
            session.commit()
        finally:
            session.close()
    
    async def _calculate_precision_proxy(
        self,
        run_id: str,
        question: str, 
        messages: List
    ) -> float:
        """Calculate precision proxy based on domain term presence."""
        if not messages:
            return 0.0
        
        domain_terms = [
            'coolsculpting', 'elite', 'return', 'rma', 'thermal', 'sensor',
            'freight', 'packaging', 'credit', 'allergan', 'abbvie'
        ]
        
        matching_messages = 0
        for msg in messages:
            text = f"{msg.subject} {msg.body}".lower()
            if any(term in text for term in domain_terms):
                matching_messages += 1
        
        return matching_messages / len(messages)
    
    async def _check_stopping_conditions(
        self, 
        metrics: List[IterationMetrics],
        config: RunConfig
    ) -> Tuple[bool, Optional[str]]:
        """Check if run should stop."""
        if len(metrics) < 2:
            return False, None
        
        last_two = metrics[-2:]
        
        # Check novelty gain
        if all(m.novelty_gain < config.min_novelty_gain for m in last_two):
            return True, f"novelty<{config.min_novelty_gain} for 2 rounds"
        
        # Check precision  
        if all(m.precision_proxy < config.min_precision for m in last_two):
            return True, f"precision<{config.min_precision} for 2 rounds"
        
        return False, None
    
    async def _normalize_and_chunk(self, run_id: str) -> None:
        """Normalize messages and create text chunks."""
        session = get_session()
        try:
            messages = session.query(Message).filter(Message.run_id == run_id).all()
            
            for msg in messages:
                # Get full body (in real implementation, would fetch from cache/Gmail)
                full_messages = await self.gmail.fetch_bodies([msg.gmail_id])
                if not full_messages:
                    continue
                
                full_msg = full_messages[0]
                
                # Clean and chunk text
                cleaned_text = self.text_processor.clean_email_body(full_msg.body)
                chunks = self.text_processor.chunk_text(
                    cleaned_text,
                    chunk_size=800,
                    overlap=100
                )
                
                # Store chunks
                for i, chunk_text in enumerate(chunks):
                    chunk_id = f"{msg.gmail_id}_{i}"
                    chunk = Chunk(
                        run_id=run_id,
                        chunk_id=chunk_id,
                        gmail_id=msg.gmail_id,
                        idx=i,
                        text=chunk_text,
                        token_count=len(chunk_text.split())
                    )
                    session.add(chunk)
            
            session.commit()
        finally:
            session.close()
    
    async def _hybrid_ranking(self, run_id: str, question: str) -> None:
        """Perform hybrid BM25 + vector ranking."""
        session = get_session()
        try:
            chunks = session.query(Chunk).filter(Chunk.run_id == run_id).all()
            
            if not chunks:
                return
            
            # BM25 ranking
            texts = [chunk.text for chunk in chunks]
            chunk_ids = [chunk.chunk_id for chunk in chunks]
            
            await self.bm25.index(texts, chunk_ids)
            bm25_results = await self.bm25.search(question, top_k=100)
            bm25_scores = dict(bm25_results)
            
            # Vector ranking
            embeddings = await self.embed.embed(texts)
            await self.vector_store.index(embeddings, chunk_ids)
            
            question_embedding = await self.embed.embed([question])
            vector_results = await self.vector_store.search(question_embedding[0], top_k=50)
            vector_scores = dict(vector_results)
            
            # Update chunk scores
            for chunk in chunks:
                chunk.bm25_score = bm25_scores.get(chunk.chunk_id, 0.0)
                chunk.knn_score = vector_scores.get(chunk.chunk_id, 0.0)
            
            # Reranking (if available)
            candidates = [
                ScoredCandidate(
                    id=chunk.chunk_id,
                    text=chunk.text,
                    score=chunk.bm25_score * 0.7 + chunk.knn_score * 0.3
                )
                for chunk in chunks
            ]
            
            reranked = await self.rerank.rerank(question, candidates)
            rerank_scores = {c.id: c.score for c in reranked}
            
            for chunk in chunks:
                chunk.rerank_score = rerank_scores.get(chunk.chunk_id, 0.0)
                chunk.selected = chunk.rerank_score > 0.1  # Threshold
            
            session.commit()
        finally:
            session.close()
    
    async def _generate_summaries(self, run_id: str, question: str) -> None:
        """Generate thread summaries using LLM."""
        session = get_session()
        try:
            # Group chunks by thread
            chunks = session.query(Chunk).filter(
                Chunk.run_id == run_id,
                Chunk.selected == True
            ).all()
            
            messages = session.query(Message).filter(Message.run_id == run_id).all()
            msg_lookup = {msg.gmail_id: msg for msg in messages}
            
            thread_chunks = {}
            for chunk in chunks:
                msg = msg_lookup.get(chunk.gmail_id)
                if msg:
                    thread_id = msg.thread_id
                    if thread_id not in thread_chunks:
                        thread_chunks[thread_id] = []
                    thread_chunks[thread_id].append(chunk)
            
            # Generate summaries for each thread
            for thread_id, chunks in thread_chunks.items():
                chunk_texts = [c.text for c in chunks]
                
                summary_md, bullets = await self.llm.summarize(
                    chunk_texts,
                    question
                )
                
                # Store summary
                summary = Summary(
                    run_id=run_id,
                    thread_id=thread_id,
                    summary_md=summary_md,
                    bullets_json=bullets,
                    confidence=0.8  # Mock confidence
                )
                session.add(summary)
            
            session.commit()
        finally:
            session.close()
    
    async def _prepare_exports(self, run_id: str) -> None:
        """Prepare export artifacts."""
        # Placeholder - would generate PDF/CSV/JSON exports
        pass
    
    async def _finalize_run(
        self, 
        run_id: str, 
        metrics: List[IterationMetrics],
        duration_ms: int
    ) -> None:
        """Finalize run with metrics and status."""
        session = get_session()
        try:
            run = session.query(Run).filter(Run.run_id == run_id).first()
            if run:
                run.status = RunStatus.DONE
                run.metrics_json = {
                    "iterations": len(metrics),
                    "total_duration_ms": duration_ms,
                    "final_precision": metrics[-1].precision_proxy if metrics else 0,
                    "total_messages": sum(m.new_messages for m in metrics),
                    "total_threads": sum(m.new_threads for m in metrics)
                }
                session.commit()
                
            await self.events.emit(RunEvent.RUN_COMPLETE, {
                "run_id": run_id,
                "duration_ms": duration_ms,
                "metrics": run.metrics_json
            })
        finally:
            session.close()
    
    async def _update_run_status(
        self, 
        run_id: str, 
        status: RunStatus, 
        error_msg: Optional[str] = None
    ) -> None:
        """Update run status in database."""
        session = get_session()
        try:
            run = session.query(Run).filter(Run.run_id == run_id).first()
            if run:
                run.status = status
                if error_msg:
                    if not run.metrics_json:
                        run.metrics_json = {}
                    run.metrics_json["error"] = error_msg
                session.commit()
        finally:
            session.close()
    
    async def pause_run(self, run_id: str) -> None:
        """Pause a running run."""
        self.is_paused = True
        await self._update_run_status(run_id, RunStatus.PAUSED)
    
    async def resume_run(self, run_id: str) -> None:
        """Resume a paused run."""
        self.is_paused = False
        # Continue execution would require more complex state management
    
    async def cancel_run(self, run_id: str) -> None:
        """Cancel a running run."""
        self.should_stop = True
        await self._update_run_status(run_id, RunStatus.CANCELLED)