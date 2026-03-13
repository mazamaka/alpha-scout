FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for Claude Code CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user (Claude CLI blocks bypassPermissions for root)
RUN useradd -m -s /bin/bash botuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browser deps (system packages)
RUN python -m playwright install-deps firefox

COPY . .

RUN mkdir -p /app/data /app/logs /home/botuser/.claude \
    && chown -R botuser:botuser /app /home/botuser/.claude

USER botuser

EXPOSE 8900

CMD ["python", "main.py", "--web"]
