ARG DOCKER_PYTHON_V=3.14-slim

# Stage 1: Build dependencies
FROM python:${DOCKER_PYTHON_V} AS builder

WORKDIR /app

ENV PIP_ROOT_USER_ACTION=ignore \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIPENV_VENV_IN_PROJECT=1

RUN pip install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv sync

# Stage 2: Runtime image
FROM python:${DOCKER_PYTHON_V} AS runtime

ARG DOCKER_PYTHON_V

# Labels that never change between builds. docker.yml adds created, revision and version.
LABEL org.opencontainers.image.title="Anything Goes Archive" \
    org.opencontainers.image.description="Self-hosted archiver and searchable web UI for browsing r/fantasybaseball's Anything Goes threads." \
    org.opencontainers.image.url="https://github.com/wazam/r-fantasybaseball-indexer" \
    org.opencontainers.image.source="https://github.com/wazam/r-fantasybaseball-indexer" \
    org.opencontainers.image.documentation="https://github.com/wazam/r-fantasybaseball-indexer#readme" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.authors="James Wazam" \
    org.opencontainers.image.vendor="wazam" \
    org.opencontainers.image.base.name="docker.io/library/python:${DOCKER_PYTHON_V}"

ARG USERNAME=appuser
ARG USER_UID=1000
ARG USER_GID=${USER_UID}
RUN groupadd --gid ${USER_GID} ${USERNAME} && \
    useradd --uid ${USER_UID} --gid ${USER_GID} --create-home ${USERNAME}

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /app/.venv/ /app/.venv/
COPY app/ ./app/
COPY entrypoint.sh /entrypoint.sh

RUN mkdir -p /app/data && chown ${USER_UID}:${USER_GID} /app/data && \
    chmod +x /entrypoint.sh

USER ${USER_UID}:${USER_GID}

EXPOSE 9009/tcp

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["./.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9009/health', timeout=3)"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["./.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9009", "--log-config", "app/logging_config.json"]
