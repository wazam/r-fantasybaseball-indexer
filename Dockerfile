ARG DOCKER_PYTHON_V=3.14-slim

# Stage 1: Build dependencies
FROM python:${DOCKER_PYTHON_V} AS builder

WORKDIR /app

# Quiet pip's running-as-root and version-check notices during the build, and keep the venv in the project
ENV PIP_ROOT_USER_ACTION=ignore \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIPENV_VENV_IN_PROJECT=1

RUN pip install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv sync

# Stage 2: Runtime image
FROM python:${DOCKER_PYTHON_V} AS runtime

ARG DOCKER_PYTHON_V

# Labels that don't change between builds. Docker Publish adds created, revision and version, so local
# builds leave them out rather than guess, and reads the description from here for GHCR's package page
LABEL org.opencontainers.image.title="Anything Goes Archive" \
    org.opencontainers.image.description="Self-hosted archiver and searchable web UI for browsing r/fantasybaseball's Anything Goes threads" \
    org.opencontainers.image.url="https://github.com/wazam/r-fantasybaseball-indexer" \
    org.opencontainers.image.source="https://github.com/wazam/r-fantasybaseball-indexer" \
    org.opencontainers.image.documentation="https://github.com/wazam/r-fantasybaseball-indexer#readme" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.authors="James Wazam" \
    org.opencontainers.image.vendor="wazam" \
    org.opencontainers.image.base.name="docker.io/library/python:${DOCKER_PYTHON_V}"

# The root filesystem may be read-only (hardened stacks), so Python doesn't write .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder /app/.venv/ ./.venv/
COPY app/ ./app/
COPY --chmod=755 entrypoint.sh /entrypoint.sh

# Owned by the default runtime UID; to run as another user with user:, mount a data folder owned by that user
RUN mkdir -p /app/data && \
    chown 1000:1000 /app/data

EXPOSE 9009/tcp

USER 1000:1000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --start-interval=5s --retries=3 \
    CMD ["./.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9009/health', timeout=3)"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["./.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9009", "--log-config", "app/logging_config.json"]
