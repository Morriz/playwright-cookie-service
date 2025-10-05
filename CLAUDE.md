# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Python Environment

**ALWAYS use the `.venv` virtual environment for ALL Python operations!**

```bash
# Activate venv first
source .venv/bin/activate

# Then run any Python commands
pip install -r requirements.txt
python test_playwright_service.py
```

## CRITICAL: Testing After Code Changes

**ALWAYS run unit tests after making any code changes!**

```bash
# After any code change, run:
make test

# For changes to core logic, also run integration test:
make test-integration

# Or run all tests:
make test-all
```

If tests fail, fix the code before proceeding. Do not commit or suggest changes without verifying tests pass.

## Project Overview

A Claude + Playwright MCP microservice that automates X (Twitter) authentication and cookie retrieval with webhook-based async processing. Claude Sonnet 4.5 orchestrates browser automation intelligently via Playwright MCP tools, adapting to page state instead of using brittle hardcoded selectors.

**Key Feature**: Webhook-based async architecture - requests return immediately with a request_id, and results are POSTed to the provided webhook URL when complete (typically 1-3 minutes).

## Architecture

Flat project structure with all Python files at root:

- **FastAPI Service** (`main.py`): Endpoint `/get-cookies` with background task processing and webhook callbacks
- **Claude Agent** (`claude_agent.py`): Agentic loop - Claude makes decisions about browser actions
- **MCP Client** (`mcp_client.py`): Manages stdio connection to Playwright MCP server
- **Models** (`models.py`): Pydantic schemas (CookieRequest, WebhookPayload, TaskStatusResponse)
- **Logger** (`lib/logger.py`): Shared logging configuration for all components
- **Docker**: Service runs in containerized environment with Node.js + Playwright MCP + Xvfb

## Development Commands

```bash
# ALWAYS activate venv first!
source .venv/bin/activate

# Install dependencies
make install

# Run unit tests
make test

# Start service locally
uvicorn main:app --reload

# Manual end-to-end test:
# Terminal 1: Start webhook receiver
python test_webhook_receiver.py

# Terminal 2: Run manual test
python test_playwright_service.py

# Docker (production)
make docker-up
# or
docker compose up --build
```

## Testing Requirements

Set these environment variables in `.env`:
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude
- `X_USERNAME` - X account username
- `X_EMAIL` - X account email
- `X_PASSWORD` - X account password
- `PROTONMAIL_EMAIL` - ProtonMail email for verification
- `PROTONMAIL_PASSWORD` - ProtonMail password

## Authentication Flow (Webhook-Based)

Client POSTs credentials + webhook_url to `/get-cookies`, receives immediate response with request_id. Service processes in background and POSTs results to webhook URL when complete.

**Background Processing**: Claude orchestrates the flow intelligently via Playwright MCP tools:
1. Navigate to X login page
2. Enter username and submit
3. Handle email/phone verification if requested
4. Enter password and submit
5. If verification code required:
   - Navigate to ProtonMail
   - Login and search for X verification email
   - Extract 6-8 digit code
   - Return to X and enter code
6. Wait for successful login (URL contains '/home')
7. Use `browser_evaluate` to extract raw cookie string via `document.cookie`
8. POST webhook callback with cookie string or error details

## Key Implementation Details

- **Webhook Architecture**: FastAPI BackgroundTasks + httpx for async webhook callbacks
- **Request Tracking**: UUIDs for correlating requests with webhook responses
- **Agentic Architecture**: Claude decides what actions to take based on page state
- **MCP Tools**: Browser automation via Playwright MCP server (stdio connection)
- **Adaptive**: No hardcoded selectors - Claude uses `browser_snapshot` to see page and adapt
- **Validation**: Cookie string validated before acceptance, Claude can self-correct
- **Cookie Format**: Raw cookie string from `document.cookie`
- **Logging**: Comprehensive logging via shared `lib/logger.py` module (INFO level)
