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

A Claude + Playwright MCP microservice that automates web authentication and cookie retrieval with webhook-based async processing. Claude Sonnet 4.5 orchestrates browser automation intelligently via Playwright MCP tools, adapting to page state instead of using brittle hardcoded selectors.

**Key Features**:

- **Generic Login URL**: Accepts any login URL, not limited to X/Twitter
- **Webhook-based async architecture**: Requests return immediately with a request_id, and results are POSTed to the provided webhook URL when complete (typically 1-3 minutes)

## Architecture

Flat project structure with all Python files at root:

- **FastAPI Service** (`main.py`): Endpoint `/get-cookies` accepts `login_url` + credentials, processes via background task with webhook callbacks
- **Claude Agent** (`claude_agent.py`): Agentic loop - Claude makes decisions about browser actions
- **MCP Client** (`mcp_client.py`): Manages stdio connection to Playwright MCP server
- **Models** (`models.py`): Pydantic schemas with `login_url` field (CookieRequest, WebhookPayload, TaskStatusResponse)
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
python webhook_receiver.py

# Terminal 2: Send test request

# Traditional username/password flow:
curl -X POST http://localhost:8000/get-cookies \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "login_url": "https://x.com/login",
    "svc_username": "your_username",
    "svc_email": "your_email",
    "svc_password": "your_password",
    "email_password": "your_email_password",
    "callback_url": "http://localhost:9000/webhook"
  }'

# Magic link flow (no username/password needed):
curl -X POST http://localhost:8000/get-cookies \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your_api_key" \
  -d '{
    "login_url": "https://example.com/login",
    "svc_email": "your_email",
    "email_password": "your_email_password",
    "callback_url": "http://localhost:9000/webhook"
  }'

# Docker (production)
make docker-up
# or
docker compose up --build
```

## Testing Requirements

Set these environment variables in `.env`:

- `ANTHROPIC_API_KEY` - Anthropic API key for Claude
- `SVC_EMAIL` - Service account email (required)
- `EMAIL_PASSWORD` - Email password for 2FA (required)
- `SVC_USERNAME` - Service account username (optional, for username/password flows)
- `SVC_PASSWORD` - Service account password (optional, for username/password flows)

## Authentication Flow (Webhook-Based)

Client POSTs `login_url` + credentials + callback_url to `/get-cookies`, receives immediate response with request_id. Service processes in background and POSTs results to webhook URL when complete.

**Supported Authentication Types:**
- **Username/Password**: Traditional login with username, email, and password
- **Magic Link**: Email-only login where service sends a login link to email

**Required Fields:**
- `login_url` - URL to the login page
- `svc_email` - Service account email
- `email_password` - ProtonMail password for retrieving verification codes/magic links
- `callback_url` - URL to receive results

**Optional Fields:**
- `svc_username` - Service account username (for username/password flows)
- `svc_password` - Service account password (for username/password flows)

**Background Processing**: Claude orchestrates the flow intelligently via Playwright MCP tools:

1. Navigate to provided login URL
2. If `svc_username` provided: Enter username and submit
3. Handle email/phone verification if requested
4. If `svc_password` provided: Enter password and submit
5. If verification code or magic link required:
   - Navigate to ProtonMail
   - Login and search for service verification email or magic link
   - Extract code/link and complete authentication
6. Wait for successful login (URL contains '/home' or similar)
7. Extract cookies from network request headers using `browser_network_requests`
   - HttpOnly cookies (like `auth_token`) aren't accessible via `document.cookie`
   - Must get Cookie header from actual HTTP requests matching the login URL
8. POST webhook callback with cookie string or error details

## Key Implementation Details

- **Dynamic Login URL**: Accepts any login URL via request parameter, not hardcoded
- **Webhook Architecture**: FastAPI BackgroundTasks + httpx for async webhook callbacks
- **Request Tracking**: UUIDs for correlating requests with webhook responses
- **Agentic Architecture**: Claude decides what actions to take based on page state
- **MCP Tools**: Browser automation via Playwright MCP server (stdio connection)
- **Adaptive**: No hardcoded selectors - Claude uses `browser_snapshot` to see page and adapt
- **Validation**: Cookie string validated before acceptance, Claude can self-correct
- **Cookie Format**: Raw cookie string from Cookie header in network requests to login URL (includes HttpOnly cookies)
- **Logging**: Comprehensive logging via shared `lib/logger.py` module (INFO level)
