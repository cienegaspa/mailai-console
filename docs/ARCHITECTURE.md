# MailAI Console Architecture

This document describes the technical architecture, design decisions, and component interactions for the MailAI Console system.

## System Overview

MailAI Console is a **local-first, full-stack application** designed for attorney Gmail evidence analysis. The system follows a **microservice-inspired architecture** with clear separation between UI, API, business logic, and data layers.

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Runs List   │  │ Run Detail  │  │ Evidence Viewer         │  │
│  │ - Create    │  │ - Progress  │  │ - Thread Messages       │  │
│  │ - Monitor   │  │ - Chat Q&A  │  │ - Citations             │  │
│  │ - Export    │  │ - Timeline  │  │ - Highlighted Quotes    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                       ┌────────────────┐
                       │ HTTP + SSE     │
                       └────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                        REST API LAYER                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Run         │  │ Events      │  │ Evidence               │  │
│  │ Management  │  │ Streaming   │  │ Retrieval              │  │
│  │ - CRUD ops  │  │ - SSE       │  │ - Threads              │  │
│  │ - Control   │  │ - Progress  │  │ - Messages             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Run         │  │ Event       │  │ Progress               │  │
│  │ Orchestrator│  │ Emitter     │  │ Tracker                │  │
│  │ - State     │  │ - Real-time │  │ - ETA estimation       │  │
│  │ - Control   │  │ - Pub/Sub   │  │ - Phase management     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                      PROVIDER LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Gmail       │  │ AI Models   │  │ Storage                │  │
│  │ - Search    │  │ - Embedding │  │ - Vector Store         │  │
│  │ - Fetch     │  │ - Rerank    │  │ - BM25                 │  │
│  │ - OAuth     │  │ - LLM       │  │ - File System          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ SQLite      │  │ File Store  │  │ Cache                  │  │
│  │ - Metadata  │  │ - Exports   │  │ - Vectors              │  │
│  │ - Results   │  │ - Logs      │  │ - Indices              │  │
│  │ - History   │  │ - Bodies    │  │ - Models               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Design Principles

### 1. Local-First Architecture

**Principle**: All sensitive data remains on the user's machine.

**Implementation**:
- SQLite database for metadata and results
- Local file storage for cached email bodies
- No cloud dependencies for core functionality  
- Optional API calls only for enhancement (query planning, summary polishing)

**Benefits**:
- PHI/PII compliance
- No internet dependency once set up
- Full data ownership
- Instant performance

### 2. Pluggable Provider System

**Principle**: Abstract external services behind interfaces to enable easy swapping.

**Implementation**:
```python
# Provider interfaces
class GmailProvider(ABC):
    async def search(query_str: str) -> List[MessageMeta]
    async def fetch_bodies(message_ids: List[str]) -> List[Message]

class EmbedProvider(ABC):
    async def embed(texts: List[str]) -> np.ndarray
    property dimension -> int

class LLMProvider(ABC):
    async def summarize(chunks: List[str], topic: str) -> Tuple[str, List[Dict]]
    async def answer(question: str, evidence: List[str]) -> Tuple[str, List[Citation], float]
```

**Benefits**:
- Easy A/B testing of AI models
- Graceful degradation (mock → local → API)
- Future-proof against service changes
- Cost optimization (cheap local models vs. API calls)

### 3. Event-Driven Real-Time Updates

**Principle**: Provide transparent, real-time feedback during long-running operations.

**Implementation**:
```python
# Event system
class RunOrchestrator:
    async def execute_run(run_id: str):
        await self.events.emit(RunEvent.RUN_STARTED, {"run_id": run_id})
        # ... work ...
        await self.events.emit(RunEvent.ITERATION_COMPLETE, {"metrics": ...})
        # ... more work ...
        await self.events.emit(RunEvent.RUN_COMPLETE, {"results": ...})

# SSE streaming
@app.get("/runs/{run_id}/events")
async def stream_events(run_id: str):
    return EventSourceResponse(event_generator(run_id))
```

**Benefits**:
- User confidence during long operations
- Early problem detection
- Progress estimation
- Better UX than polling

## Component Deep Dive

### Run Orchestrator (Core Business Logic)

The **RunOrchestrator** is the heart of the system, implementing the iterative retrieval algorithm:

```python
async def execute_run(self, run_id: str, config: RunConfig):
    # Phase 1: Iterative retrieval with term expansion
    metrics = await self._iterative_retrieval(run_id, config)
    
    # Phase 2: Normalization and chunking  
    await self._normalize_and_chunk(run_id)
    
    # Phase 3: Hybrid ranking (BM25 + Vector + Rerank)
    await self._hybrid_ranking(run_id, config.question)
    
    # Phase 4: LLM summarization with citations
    await self._generate_summaries(run_id, config.question)
    
    # Phase 5: Export preparation
    await self._prepare_exports(run_id)
```

**State Machine**:
```
QUEUED → FETCHING → NORMALIZING → RANKING → ITERATING → SUMMARIZING → EXPORTING → DONE/FAILED
```

**Stopping Conditions**:
- Novelty gain < 2% for 2 consecutive iterations
- Precision proxy < 30% for 2 consecutive iterations  
- Max iterations reached (configurable, default 4)
- User cancellation

### Iterative Retrieval Algorithm

**Phase 1: Seed Query Generation**
```python
# Extract key terms from user question
key_terms = extract_terms("CoolSculpting Elite return issues")
# → ["CoolSculpting", "Elite", "return", "issues"]

# Generate Gmail operator patterns
patterns = [
    f'("return" OR "RMA") ("CoolSculpting Elite")',
    f'("CoolSculpting" AND "Elite") AND ("thermal" OR "error")', 
    f'("credit" OR "refund") ("CoolSculpting Elite")'
]
```

**Phase 2: Term Expansion**
```python
# Analyze top-ranked chunks for co-occurring terms
def expand_terms(messages, current_terms):
    # Extract logistics terms: ["waybill", "bill of lading", "palletize"]
    # Extract technical terms: ["thermal sensor", "error code E-47"]  
    # Extract process terms: ["credit memo", "manufacturing defect"]
    # Extract sender patterns: ["returns@allergan.com", "logistics@abbvie.com"]
    return expanded_terms
```

**Phase 3: Query Refinement**
```python  
# Generate new queries using learned terms
new_queries = [
    f'("waybill" OR "bill of lading") from:allergan.com',
    f'("Error Code E-47" OR "thermal sensor") ("CoolSculpting")',  
    f'("manufacturing defect" OR "inspection") ("credit")'
]
```

### Hybrid Ranking System

**Multi-stage ranking pipeline**:

1. **BM25 Prefilter** (lexical matching)
   ```python
   # Index all chunks with BM25
   bm25_scores = bm25.search(question, top_k=100)
   ```

2. **Vector Similarity** (semantic matching)  
   ```python
   # Embed chunks and query
   embeddings = await embed_provider.embed(chunk_texts)
   query_embedding = await embed_provider.embed([question])
   vector_scores = vector_store.search(query_embedding, top_k=50)
   ```

3. **Cross-Encoder Reranking** (optional)
   ```python
   # Rerank top candidates for relevance
   candidates = create_candidates(chunks, hybrid_scores)
   reranked = await rerank_provider.rerank(question, candidates)
   ```

4. **Score Fusion**
   ```python
   final_score = 0.3 * bm25_score + 0.4 * vector_score + 0.3 * rerank_score
   ```

### Citation System

**Direct Quote Extraction**:
```python
def extract_quotes(text: str, min_length: int = 10) -> List[str]:
    sentences = split_sentences(text)
    return [s for s in sentences if has_domain_terms(s) and len(s) >= min_length]
```

**Citation Format**: `[gmail_id|thread_id|date]`
- `gmail_id`: Unique Gmail message identifier
- `thread_id`: Gmail conversation thread ID
- `date`: ISO format date for precise temporal reference

**Example**:
> "The unit has been experiencing consistent temperature regulation issues" 
> [G-001|T-001|2025-02-01]

### Database Schema Design

**Normalized relational design** with clear separation of concerns:

```sql
-- Core run metadata
runs(run_id PK, question, params_json, status, metrics_json)

-- Query execution history  
queries(id PK, run_id FK, iteration, query_str, hits, new_msgs)

-- Term expansion tracking
terms(id PK, run_id FK, iteration, added_terms_json, evidence_terms_json)

-- Global message deduplication
global_messages(gmail_id PK, thread_id, date, from_email, body_path)
global_chunks(chunk_id PK, gmail_id FK, text, token_count)  

-- Run-specific evidence sets
messages(id PK, run_id FK, gmail_id, selected BOOL)
chunks(id PK, run_id FK, chunk_id, bm25_score, vector_score, rerank_score)

-- AI-generated summaries
summaries(id PK, run_id FK, thread_id, summary_md, bullets_json, confidence)
```

**Design rationale**:
- **Global tables** for deduplication across runs
- **Run-specific tables** for evidence sets and scores  
- **JSON fields** for flexible metadata storage
- **Indexes** on common query patterns (date, from_email, scores)

## Performance Considerations

### Scalability Targets

**Current scale (Mac mini M-class)**:
- ✅ **Email volume**: 1K-10K messages per run
- ✅ **Response time**: 1-3 minutes end-to-end  
- ✅ **Memory usage**: <2GB including AI models
- ✅ **Storage**: ~100MB per 1K messages with vectors

**Optimization strategies**:
- **Lazy loading**: Fetch message bodies only when needed
- **Chunk caching**: Reuse text processing across runs
- **Vector quantization**: Reduce memory footprint  
- **Incremental indexing**: Update rather than rebuild indices

### Real-Time Performance

**SSE latency targets**:
- Event emission: <10ms
- UI update: <100ms  
- Progress granularity: Every 5% completion

**ETA estimation algorithm**:
```python
def estimate_eta(elapsed_ms: int, progress_pct: float) -> int:
    if progress_pct < 0.05:  # Less than 5% complete
        return None  # Too early to estimate
    
    estimated_total = elapsed_ms / progress_pct
    remaining_ms = estimated_total - elapsed_ms
    return max(remaining_ms, 0)
```

## Security & Privacy

### Local Data Hygiene

**Principle**: Treat all email content as sensitive PHI/PII.

**Implementation**:
- **No cloud sync**: Database and cache files excluded from cloud backup
- **Encryption at rest**: Recommend FileVault on macOS
- **Token security**: OAuth tokens stored in system keychain
- **Log sanitization**: No email content in application logs

### Access Control

**Current model**: Single-user local application
**Future consideration**: Multi-user with role-based access

```python
# Token rotation
async def refresh_gmail_token():
    if token_expires_within(hours=1):
        new_token = await oauth_client.refresh_token()
        store_token_securely(new_token)
```

## Deployment & Operations

### Development Setup

**Prerequisites**:
- Python 3.9+ with pip
- Node.js 18+ with npm  
- 8GB+ RAM (for local AI models)
- 10GB+ disk space

**Setup flow**:
```bash
make setup    # Install deps, create DB, download models
make dev      # Start backend + frontend
make test     # Run test suite
```

### Production Considerations

**Mock vs Real mode**:
- **Mock mode** (default): Works immediately, no credentials
- **Real mode**: Requires Gmail OAuth setup, local AI models

**Configuration management**:
```bash
# .env file with sensible defaults
MAILAI_MOCKS=true              # Start in demo mode
MAILAI_DB_PATH=./db/mailai.sqlite
EMBED_MODEL=gte-small          # CPU-friendly default
LLM_MODEL=llama3.1:8b-q5      # Balance of speed/quality
```

**Monitoring**:
- Structured logging (JSON format)
- Performance metrics per run phase
- Error tracking and alerting
- Database size monitoring

## Future Architecture Evolution

### V2 Enhancements

**Multi-modal evidence**:
- PDF attachment processing
- Image OCR for scanned documents  
- Calendar integration for timeline analysis

**Distributed compute**:
- Offload AI processing to RTX server
- Kubernetes deployment for enterprise
- Federated search across multiple Gmail accounts

**Advanced AI**:
- Multi-agent orchestration (specialist agents per domain)
- Knowledge graph construction from evidence
- Adversarial validation of conclusions

### V3 Vision

**Legal workflow integration**:
- Discovery management platform integration
- Deposition preparation assistance  
- Brief writing with evidence linking
- Regulatory compliance checking

**Cross-platform expansion**:
- Outlook integration
- Slack/Teams evidence gathering
- Cloud storage document analysis
- CRM system integration

---

This architecture balances **immediate utility** (works in mock mode), **professional requirements** (citations, audit trails), and **future scalability** (pluggable providers, event-driven design).

The system is designed to be **locally powerful** while remaining **cloud-ready** for future enterprise deployment scenarios.