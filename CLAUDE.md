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

### Testing Individual Components

```bash
# Backend tests
cd backend && python3 -m pytest tests/ -v
cd backend && python3 -m pytest tests/test_specific.py -v

# Frontend tests  
cd frontend && npm test
cd frontend && npm run lint
cd frontend && npm run build

# Backend linting and formatting
cd backend && python3 -m flake8 mailai/
cd backend && python3 -m black mailai/ tests/

# Frontend linting and formatting
cd frontend && npm run lint
cd frontend && npx prettier --write src/
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
- **Gmail**: Real OAuth vs Mock fixtures (see OAUTH_SETUP.md for configuration)
- **Embeddings**: Local sentence-transformers vs API calls
- **LLM**: Local Ollama vs API (GPT-4o-mini)
- **Reranker**: Local cross-encoder vs disabled

- **Vector Store**: FAISS for similarity search

### Gmail OAuth Setup
To enable real Gmail connections, you must configure Google OAuth credentials. See `OAUTH_SETUP.md` for detailed instructions on:
- Creating a Google Cloud Project
- Enabling Gmail API
- Setting up OAuth consent screen  
- Generating client credentials
- Configuring environment variables

## Key Configuration

Environment controlled via `.env` (see `.env.example` for full configuration):
```bash
# Core settings
MAILAI_MOCKS=true              # Use mock providers (default for development)
MAILAI_API_PORT=5170           # Backend API port
MAILAI_UI_PORT=5171            # Frontend dev server port
MAILAI_DB_PATH=./db/mailai.sqlite

# AI Provider configuration (when MAILAI_MOCKS=false)
EMBED_PROVIDER=local           # local or api
EMBED_MODEL=gte-small
RERANK_PROVIDER=local          # local or off
LLM_PROVIDER=local             # local or api  
LLM_MODEL=llama3.1:8b-q5

# Gmail OAuth (real mode)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_SCOPES=https://www.googleapis.com/auth/gmail.readonly
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

### Browser Automation & Screenshots
**FOLLOWS GLOBAL STANDARD**: All Puppeteer automation uses `/Users/tom/Projects/GLOBAL_PUPPETEER_CONFIG.js`

```javascript
// REQUIRED: Import global configuration for consistent behavior
const { getGlobalPuppeteerConfig } = require('../GLOBAL_PUPPETEER_CONFIG.js');
const browser = await puppeteer.launch(getGlobalPuppeteerConfig());
```

**Benefits**: Headless mode prevents focus stealing, consistent settings across all projects, edit once to change everywhere.

## Provider Switching

To use real providers instead of mocks:
1. Set `MAILAI_MOCKS=false` in `.env`
2. Configure OAuth credentials for Gmail (see `OAUTH_SETUP.md`)
3. Install local AI models (Ollama recommended):
   ```bash
   ollama pull llama3.1:8b-q5
   ollama pull gte-small
   ```
4. Restart with `make dev`

## Development Stack

- **Backend**: FastAPI 0.104.1 + SQLAlchemy 2.0.23 + Python 3.9+
- **Frontend**: React 18 + Vite + TypeScript + Tailwind CSS
- **AI/ML**: sentence-transformers, FAISS, torch, transformers
- **Testing**: pytest (backend), built-in Vite tests (frontend)
- **Formatting**: black (Python), prettier (frontend)
- **Linting**: flake8 (Python), ESLint (frontend)

## Workspace Integration

This project is part of a shared Claude Code workspace. Shared tools and configurations:

- **Auto-initialization**: Run `./claude-init` to discover available development tools
- **Shared configs**: Access global configurations via workspace integration
- **Global standards**: Follows workspace-wide coding and testing standards

### Quick Commands
- `./claude-init` - Initialize Claude with current environment capabilities
- `../..claude-workspace/init/claude-init.sh` - Detailed tool discovery
- Access shared configs in `../../.claude-workspace/configs/`
