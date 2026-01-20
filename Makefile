# Painminer Project Makefile
# =========================

# Variables
PYTHON := ./venv/bin/python
PIP := ./venv/bin/pip
PROJECT_ROOT := $(shell pwd)
WEB_DIR := $(PROJECT_ROOT)/web

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

# Default target
.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)Painminer Project Commands$(NC)"
	@echo "=========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Setup and Installation
.PHONY: setup
setup: ## Setup virtual environment and install dependencies
	@echo "$(YELLOW)Setting up Python virtual environment...$(NC)"
	python3 -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	$(PIP) install uvicorn fastapi
	@echo "$(YELLOW)Installing web dependencies...$(NC)"
	cd $(WEB_DIR) && npm install
	@echo "$(GREEN)Setup complete!$(NC)"

.PHONY: setup-dev
setup-dev: ## Setup development environment with dev dependencies
	@echo "$(YELLOW)Setting up development environment...$(NC)"
	python3 -m venv venv
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	$(PIP) install uvicorn fastapi
	cd $(WEB_DIR) && npm install
	@echo "$(GREEN)Development setup complete!$(NC)"

# Development Commands
.PHONY: api
api: ## Start the API server
	@echo "$(YELLOW)Starting API server on http://localhost:8000...$(NC)"
	$(PYTHON) -m uvicorn painminer.api:app --reload --host 0.0.0.0 --port 8000

.PHONY: web
web: ## Start the web interface
	@echo "$(YELLOW)Starting web interface on http://localhost:3000...$(NC)"
	cd $(WEB_DIR) && npm run dev

.PHONY: dev
dev: ## Start both API and web interface in background
	@echo "$(YELLOW)Starting full development environment...$(NC)"
	@echo "$(BLUE)API server: http://localhost:8000$(NC)"
	@echo "$(BLUE)Web interface: http://localhost:3000$(NC)"
	@make api & make web &
	@wait

.PHONY: build-web
build-web: ## Build the web interface for production
	@echo "$(YELLOW)Building web interface...$(NC)"
	cd $(WEB_DIR) && npm run build

.PHONY: start-web
start-web: ## Start production web server
	@echo "$(YELLOW)Starting production web server...$(NC)"
	cd $(WEB_DIR) && npm start

# CLI Commands
.PHONY: run
run: ## Run painminer CLI with sample config (requires Reddit credentials)
	@echo "$(YELLOW)Running Painminer CLI...$(NC)"
	$(PYTHON) -m painminer run --config sample_config.yaml --out output.md --verbose

.PHONY: run-json
run-json: ## Run painminer CLI with JSON output
	@echo "$(YELLOW)Running Painminer CLI with JSON output...$(NC)"
	$(PYTHON) -m painminer run --config sample_config.yaml --out report.json --verbose

.PHONY: run-no-cache
run-no-cache: ## Run painminer CLI without cache
	@echo "$(YELLOW)Running Painminer CLI without cache...$(NC)"
	$(PYTHON) -m painminer run --config sample_config.yaml --out output.md --no-cache --verbose

# Cache Management
.PHONY: cache-stats
cache-stats: ## Show cache statistics
	@echo "$(YELLOW)Cache statistics:$(NC)"
	$(PYTHON) -m painminer cache --stats

.PHONY: cache-clear
cache-clear: ## Clear all cached data
	@echo "$(YELLOW)Clearing cache...$(NC)"
	$(PYTHON) -m painminer cache --clear
	@echo "$(GREEN)Cache cleared!$(NC)"

# Testing
.PHONY: test
test: ## Run all tests
	@echo "$(YELLOW)Running tests...$(NC)"
	$(PYTHON) -m pytest

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	$(PYTHON) -m pytest --cov=painminer --cov-report=html --cov-report=term

.PHONY: test-verbose
test-verbose: ## Run tests with verbose output
	@echo "$(YELLOW)Running tests (verbose)...$(NC)"
	$(PYTHON) -m pytest -v

# Code Quality
.PHONY: lint
lint: ## Run linting checks
	@echo "$(YELLOW)Running linting checks...$(NC)"
	$(PYTHON) -m ruff check painminer/
	$(PYTHON) -m mypy painminer/

.PHONY: format
format: ## Format code with ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	$(PYTHON) -m ruff format painminer/

.PHONY: lint-web
lint-web: ## Lint web interface code
	@echo "$(YELLOW)Linting web interface...$(NC)"
	cd $(WEB_DIR) && npm run lint

# Cleanup
.PHONY: clean
clean: ## Clean up temporary files and caches
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf build/ dist/ *.egg-info/
	rm -rf .coverage htmlcov/
	cd $(WEB_DIR) && rm -rf .next/ node_modules/.cache/

.PHONY: clean-all
clean-all: clean ## Clean everything including node_modules and venv
	@echo "$(YELLOW)Deep cleaning...$(NC)"
	rm -rf venv/
	cd $(WEB_DIR) && rm -rf node_modules/
	@echo "$(GREEN)Deep clean complete!$(NC)"

# Utility Commands
.PHONY: install
install: ## Install package in development mode
	@echo "$(YELLOW)Installing painminer package...$(NC)"
	$(PIP) install -e .

.PHONY: upgrade
upgrade: ## Upgrade all Python dependencies
	@echo "$(YELLOW)Upgrading Python dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -e ".[dev]"
	$(PIP) install --upgrade uvicorn fastapi

.PHONY: upgrade-web
upgrade-web: ## Upgrade web dependencies
	@echo "$(YELLOW)Upgrading web dependencies...$(NC)"
	cd $(WEB_DIR) && npm update

.PHONY: check-env
check-env: ## Check if environment variables are set
	@echo "$(YELLOW)Checking Reddit API environment variables...$(NC)"
	@if [ -z "$$REDDIT_CLIENT_ID" ]; then echo "$(RED)REDDIT_CLIENT_ID not set$(NC)"; else echo "$(GREEN)REDDIT_CLIENT_ID: set$(NC)"; fi
	@if [ -z "$$REDDIT_CLIENT_SECRET" ]; then echo "$(RED)REDDIT_CLIENT_SECRET not set$(NC)"; else echo "$(GREEN)REDDIT_CLIENT_SECRET: set$(NC)"; fi
	@if [ -z "$$REDDIT_USERNAME" ]; then echo "$(RED)REDDIT_USERNAME not set$(NC)"; else echo "$(GREEN)REDDIT_USERNAME: set$(NC)"; fi
	@if [ -z "$$REDDIT_PASSWORD" ]; then echo "$(RED)REDDIT_PASSWORD not set$(NC)"; else echo "$(GREEN)REDDIT_PASSWORD: set$(NC)"; fi

.PHONY: info
info: ## Show project information
	@echo "$(BLUE)Painminer Project Information$(NC)"
	@echo "============================"
	@echo "$(GREEN)Python version:$(NC) $$($(PYTHON) --version)"
	@echo "$(GREEN)Project root:$(NC) $(PROJECT_ROOT)"
	@echo "$(GREEN)Web directory:$(NC) $(WEB_DIR)"
	@echo "$(GREEN)Python executable:$(NC) $(PYTHON)"
	@echo "$(GREEN)Virtual environment:$(NC) $$([ -d venv ] && echo 'Active' || echo 'Not found')"
	@echo "$(GREEN)Web dependencies:$(NC) $$([ -d $(WEB_DIR)/node_modules ] && echo 'Installed' || echo 'Not installed')"

# Quick start commands
.PHONY: quick-start
quick-start: setup ## Quick setup and start development environment
	@echo "$(GREEN)Quick start complete! Use 'make dev' to start development servers.$(NC)"

.PHONY: all
all: setup test lint build-web ## Setup, test, lint, and build everything
	@echo "$(GREEN)All tasks completed successfully!$(NC)"