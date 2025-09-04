# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

MailAI Console is a local-only Gmail evidence analysis application for attorneys. It consists of a Python FastAPI backend, React frontend, and pluggable provider system for Gmail/AI services. The application runs iterative Gmail retrieval with AI analysis to answer legal questions and provide citation-rich summaries.

## Development Commands

All development is managed through the Makefile:

```bash
# Initial setup (run once)
make setup          # Installs all dependencies and initializes database

# Development workflow  
make dev            # Start both backend (port 5170) and frontend (port 5171) servers
make build          # Build production frontend artifacts
make test           # Run Python pytest backend tests and npm frontend tests
make lint           # Run Python flake8 and npm eslint
make format         # Run black (Python) and prettier (frontend) formatting
make clean          # Remove build artifacts, database, and cached data

# CLI interface shortcuts
make cli-run QUESTION="your question here"
make cli-list       # List all runs
make cli-show RUN_ID=<run_id>  # Show run details
```

## Architecture

### Backend Structure (`backend/`)
- **`mailai/api/main.py`** - FastAPI application with REST endpoints and Server-Sent Events
- **`mailai/core/runner.py`** - Core iterative retrieval orchestrator and task runner  
- **`mailai/models/simple_db.py`** - SQLAlchemy database models (Runs, Messages, Threads, etc.)
- **`mailai/providers/`** - Pluggable provider interfaces and mock implementations
- **`mailai/utils/`** - Text processing and event emission utilities

### Frontend Structure (`frontend/`)
- **`src/pages/`** - Main UI pages (RunsList, RunDetail, EvidenceViewer)
- **`src/utils/api.ts`** - TypeScript API client with SSE support
- **Stack**: React + Vite + Tailwind CSS + TypeScript

### Provider System
The application uses pluggable providers controlled by environment variables:
- **Gmail**: Real OAuth vs Mock fixtures 
- **Embeddings**: Local sentence-transformers vs API calls
- **LLM**: Local Ollama vs API (GPT-4o-mini)
- **Reranker**: Local cross-encoder vs disabled
- **Vector Store**: FAISS for similarity search

## Key Configuration

Environment controlled via `.env`:
```bash
MAILAI_MOCKS=true              # Use mock providers (default for development)
MAILAI_API_PORT=5170           # Backend API port
MAILAI_UI_PORT=5171            # Frontend dev server port
MAILAI_DB_PATH=./db/mailai.sqlite
```

## Core Workflow

1. **Iterative Retrieval**: Generates seed Gmail queries from user questions, executes searches, fetches message bodies
2. **Text Processing**: Normalizes HTML, removes signatures/quotes, creates 800-token chunks
3. **Hybrid Ranking**: BM25 prefilter → vector embeddings → optional reranking  
4. **Term Expansion**: Extracts co-occurring terms and sender aliases to generate new queries
5. **Stopping Logic**: Continues until novelty gain < 2% or precision < 30% for 2 consecutive iterations
6. **Citation System**: Generates summaries with direct quotes and `[gmail_id|thread_id|date]` citations

## Database Schema

SQLite database with core tables:
- **`runs`** - Query sessions with status, metrics, configuration
- **`queries`** - Gmail search operators per iteration with hit counts
- **`messages`** - Gmail message metadata and bodies  
- **`chunks`** - Text segments with embeddings for similarity search
- **`threads`** - Email thread summaries with bullets and citations

## Real-time Updates

Server-Sent Events (SSE) provide live progress updates:
- Phase transitions (fetching → ranking → iterating → summarizing)
- ETA estimates based on historical performance
- Live metrics (messages found, threads, precision proxy, novelty gain)

## Testing and Mock Data

The application ships with mock providers enabled by default using realistic "CoolSculpting Elite return scenario" data with 8+ email threads. This allows immediate testing without Gmail OAuth setup.

## Provider Switching

To use real providers instead of mocks:
1. Set `MAILAI_MOCKS=false` in `.env`
2. Configure OAuth credentials for Gmail
3. Install local AI models (Ollama recommended)
4. Restart with `make dev`