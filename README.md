# Playwright Cookie Service

A Claude + Playwright MCP microservice that automates X (Twitter) authentication and cookie retrieval. Claude Sonnet 4.5 orchestrates browser automation intelligently via Playwright MCP tools, adapting to page state instead of using brittle hardcoded selectors.

## Features

- **Agentic Architecture**: Claude decides what actions to take based on real-time page state
- **Adaptive Automation**: No hardcoded selectors - uses `browser_snapshot` to see and adapt
- **Bot Detection Evasion**: Runs in headed mode with Xvfb + stealth techniques
- **Email Verification**: Automatically handles 2FA via ProtonMail
- **Self-Correcting**: Claude validates and fixes its own outputs
- **Webhook-Based**: Async processing with webhook callbacks for long-running tasks

## Architecture

```
┌──────────────────┐
│   Client/User    │
└────────┬─────────┘
         │ POST /get-cookies (webhook_url)
         ▼
┌─────────────────┐
│  FastAPI Server │◄─── Returns immediately with request_id
│  (Background    │
│   Processing)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Claude Agent   │◄────►│ Playwright MCP   │
│  (Orchestrator) │      │  (Browser Tools) │
└─────────────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Validation &   │
│  Self-Correct   │
└────────┬────────┘
         │ POST webhook_url
         ▼
┌─────────────────┐
│  Webhook URL    │◄─── Receives final results
│  (Your Server)  │
└─────────────────┘
```

## Quick Start

### Testing

```bash
# Setup
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
make install-dev
cp .env.example .env
# Edit .env with your credentials

# Run unit tests (fast, recommended)
make test

# Run integration test (automated, ~2 minutes)
make test-integration

# Run all tests
make test-all
```

### Local Development

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate
make install
make install-dev

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Run service locally
uvicorn main:app --reload
```

### Manual End-to-End Testing

```bash
# Terminal 1: Start webhook receiver
python test_webhook_receiver.py

# Terminal 2: Start service (local or Docker)
uvicorn main:app --reload
# OR
docker compose up --build

# Terminal 3: Send test request
python test_playwright_service.py
```

## Environment Variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_anthropic_key
X_USERNAME=your_x_username
X_EMAIL=your_x_email
X_PASSWORD=your_x_password
PROTONMAIL_EMAIL=your_protonmail_email
PROTONMAIL_PASSWORD=your_protonmail_password
```

## API

### POST /get-cookies

Authenticate with X and retrieve cookies via webhook callback.

**Request:**
```json
{
  "x_username": "your_username",
  "x_email": "your_email",
  "x_password": "your_password",
  "protonmail_email": "your_protonmail",
  "protonmail_password": "your_protonmail_password",
  "webhook_url": "https://your-server.com/webhook"
}
```

**Immediate Response:**
```json
{
  "status": "processing",
  "message": "Task accepted. Results will be sent to webhook URL.",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Webhook Callback (sent to `webhook_url` when complete):**
```json
{
  "success": true,
  "cookies": "auth_token=...; ct0=...; guest_id=...",
  "iterations": 10,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Or on error:
```json
{
  "success": false,
  "error": "Login failed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Development

### Commands

```bash
# Formatting & Linting
make format       # Auto-format code with ruff and black
make lint         # Check code style with ruff
make type-check   # Run mypy type checker

# Testing
make test         # Run unit tests (pytest)

# Docker
make docker-build # Build Docker image
make docker-up    # Start services
make docker-down  # Stop services

# Cleanup
make clean        # Remove build artifacts
```

### Pre-commit Hooks

Install pre-commit hooks to automatically format and lint on commit:

```bash
pre-commit install
```

## How It Works

1. **Request Received**: Client POSTs to `/get-cookies` with credentials and webhook URL
2. **Immediate Response**: Service returns request_id and starts background processing
3. **Navigation**: Claude navigates to X login page
4. **Adaptive Input**: Uses `browser_snapshot` to see page state, then enters credentials
5. **Email Verification**: If required, switches to ProtonMail to get verification code
6. **2FA Handling**: Extracts code and returns to X to complete login
7. **Cookie Extraction**: Uses `browser_evaluate(() => document.cookie)` to get raw cookies
8. **Validation**: Validates cookie format and self-corrects if needed
9. **Webhook Callback**: POSTs final result (success or error) to provided webhook URL

## Technical Details

### Bot Detection Evasion

- **Headed Mode with Xvfb**: Runs real browser with virtual display in Docker
- **Stealth Script**: Masks automation signals (navigator.webdriver, etc.)
- **Chrome 140 User Agent**: Latest Chrome fingerprint
- **Complete Navigator Properties**: Matches real Chrome session

### Key Files

Flat project structure with all Python files at root:

- `main.py` - FastAPI service with webhook support
- `claude_agent.py` - Agentic loop for tool orchestration
- `mcp_client.py` - Playwright MCP connection manager
- `stealth.js` - Browser fingerprint evasion script
- `models.py` - Pydantic request/response schemas
- `lib/logger.py` - Shared logging configuration
- `test_webhook_receiver.py` - Test webhook endpoint (for manual testing)
- `test_playwright_service.py` - Manual end-to-end test script
- `test_webhook_unit.py` - Unit tests (pytest)

## CI/CD

GitHub Actions workflows:

- **CI** (`.github/workflows/ci.yml`): Runs linting on PRs
- **Docker** (`.github/workflows/docker.yml`): Builds and pushes image to GHCR on main/tags

## Troubleshooting

### "Browser is already in use"

The service uses `--isolated` flag. If you still see this, restart the container:

```bash
docker compose down
docker compose up --build
```

### Bot Detection / Login Fails

The service is configured for headed mode with Xvfb. If detection occurs:
- Check Chrome version matches stealth.js fingerprint
- Verify Xvfb is running (check Docker logs)
- Consider rotating IP or waiting before retry

### No Cookies Returned

Check logs for validation errors:

```bash
# Local
tail -f logs/console.txt

# Docker
docker compose logs -f
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make format && make lint && make type-check`
5. Submit a pull request
