ARG DOCKER_PYTHON_V=3.13-slim
ARG GIT_COMMIT
ARG BUILD_DATE
ARG IMAGE_VERSION

# Stage 1: Build dependencies
FROM python:${DOCKER_PYTHON_V} AS builder

WORKDIR /app

RUN pip install --no-cache-dir pipenv
ENV PIPENV_VENV_IN_PROJECT=1

COPY Pipfile Pipfile.lock ./
RUN pipenv sync

# Stage 2: Runtime image
FROM python:${DOCKER_PYTHON_V} AS runtime

ARG GIT_COMMIT
ARG BUILD_DATE
ARG IMAGE_VERSION

LABEL org.opencontainers.image.title="Anything Goes Archive" \
    org.opencontainers.image.description="Self-hosted archiver and web UI for r/fantasybaseball Anything Goes threads" \
    org.opencontainers.image.version="${IMAGE_VERSION:-unknown}" \
    org.opencontainers.image.source="https://github.com/wazam/r-fantasybaseball-indexer" \
    org.opencontainers.image.documentation="https://github.com/wazam/r-fantasybaseball-indexer#readme" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.authors="James Wazam" \
    org.opencontainers.image.vendor="wazam" \
    org.opencontainers.image.revision="${GIT_COMMIT:-unknown}" \
    org.opencontainers.image.created="${BUILD_DATE:-unknown}"

ARG USERNAME=appuser
ARG USER_UID=1000
ARG USER_GID=${USER_UID}
RUN groupadd --gid ${USER_GID} ${USERNAME} && \
    useradd --uid ${USER_UID} --gid ${USER_GID} --create-home ${USERNAME}

WORKDIR /app

COPY --from=builder /app/.venv/ /app/.venv/
COPY app/ ./app/

RUN mkdir -p /app/data && chown -R ${USERNAME}:${USERNAME} /app

EXPOSE 9009/tcp

USER ${USERNAME}

CMD ["./.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9009"]
