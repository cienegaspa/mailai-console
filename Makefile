.PHONY: help setup dev build test clean lint format install-backend install-frontend install-cli

# Default target
help:
	@echo "MailAI Console - Available commands:"
	@echo "  setup          - Full project setup (installs dependencies, creates DB)"
	@echo "  dev            - Start development servers (backend + frontend)"
	@echo "  build          - Build production artifacts"
	@echo "  test           - Run all tests"
	@echo "  lint           - Run linting"
	@echo "  format         - Format code"
	@echo "  clean          - Clean build artifacts and data"
	@echo "  install-backend - Install Python backend dependencies"
	@echo "  install-frontend - Install Node.js frontend dependencies"
	@echo "  install-cli    - Install CLI dependencies"

# Setup everything
setup: install-backend install-frontend install-cli init-db
	@echo "✅ Setup complete! Run 'make dev' to start development servers."

# Install backend dependencies
install-backend:
	@echo "Installing backend dependencies..."
	cd backend && python3 -m pip install -r requirements.txt
	@echo "✅ Backend dependencies installed"

# Install frontend dependencies  
install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ Frontend dependencies installed"

# Install CLI dependencies
install-cli:
	@echo "Installing CLI dependencies..."
	cd cli && python3 -m pip install -r requirements.txt
	@echo "✅ CLI dependencies installed"

# Initialize database
init-db:
	@echo "Initializing database..."
	mkdir -p db data exports logs
	cd backend && python3 -c "from mailai.models.database import init_db; init_db()"
	@echo "✅ Database initialized"

# Development mode
dev:
	@echo "Starting development servers..."
	@echo "Backend: http://127.0.0.1:5170"
	@echo "Frontend: http://127.0.0.1:5171"
	npx concurrently \
		"cd backend && python3 -m uvicorn mailai.api.main:app --reload --host 127.0.0.1 --port 5170" \
		"cd frontend && npm run dev -- --port 5171"

# Build production
build:
	cd frontend && npm run build
	@echo "✅ Production build complete"

# Run tests
test:
	@echo "Running backend tests..."
	cd backend && python3 -m pytest tests/ -v
	@echo "Running frontend tests..."
	cd frontend && npm test
	@echo "✅ All tests passed"

# Linting
lint:
	@echo "Linting backend..."
	cd backend && python3 -m flake8 mailai/
	@echo "Linting frontend..."
	cd frontend && npm run lint
	@echo "✅ Linting complete"

# Format code
format:
	@echo "Formatting backend..."
	cd backend && python3 -m black mailai/ tests/
	@echo "Formatting frontend..."
	cd frontend && npx prettier --write src/
	@echo "✅ Code formatted"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf frontend/dist/ frontend/build/
	rm -rf backend/__pycache__/ backend/mailai/__pycache__/
	rm -rf db/ data/ exports/ logs/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	@echo "✅ Clean complete"

# CLI shortcuts
cli-run:
	cd cli && python3 -m mailai.cli run "$(QUESTION)"

cli-list:
	cd cli && python3 -m mailai.cli list

cli-show:
	cd cli && python3 -m mailai.cli show $(RUN_ID)