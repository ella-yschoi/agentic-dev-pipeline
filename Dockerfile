FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml VERSION ./
COPY src/ src/

RUN uv sync --no-dev

COPY . .

RUN uv run pytest tests/ -v

ENTRYPOINT ["uv", "run", "agentic-dev-pipeline"]
CMD ["--help"]
