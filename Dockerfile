# Stage 1: Build + validate
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble AS builder

WORKDIR /app

# Install make
RUN apt-get update && apt-get install -y make && rm -rf /var/lib/apt/lists/*

# Copy requirements and install all dependencies (including dev)
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Copy Makefile
COPY Makefile .

# Copy source code
COPY lib/ lib/
COPY main.py models.py claude_agent.py mcp_client.py stealth.js ./

# Run lint and type checks
RUN make lint type-check

# Stage 2: Production runtime
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

# Install Node.js and Xvfb (virtual framebuffer for headed mode)
RUN apt-get update && apt-get install -y nodejs npm xvfb && rm -rf /var/lib/apt/lists/*

# Install Playwright MCP server globally
RUN npm install -g @playwright/mcp@latest

# Copy requirements and install production dependencies only
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy validated code from builder stage
COPY --from=builder /app/lib/ lib/
COPY --from=builder /app/main.py /app/models.py /app/claude_agent.py /app/mcp_client.py /app/stealth.js ./

# Expose port
EXPOSE 8080

# Run the service with Xvfb (virtual display for headed mode)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]