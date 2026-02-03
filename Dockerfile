# ------------------------------------------------------------
# Base/builder layer
# ------------------------------------------------------------

FROM python:3.12-slim-bullseye AS builder

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt clean && \
    rm -rf /var/lib/apt && \
    rm -rf /var/lib/dpkg/info/*

COPY pyproject.toml uv.lock /tmp/

RUN --mount=type=cache,target=/root/.cache,sharing=locked,id=pip \
    python -m pip install --upgrade pip uv

RUN --mount=type=cache,target=/root/.cache,sharing=locked,id=pip \
    cd /tmp && \
    python -m uv export --no-hashes --no-emit-project --all-extras --format requirements-txt -o requirements.txt && \
    python -m uv pip install --system -r requirements.txt

# ------------------------------------------------------------
# Release layer
# ------------------------------------------------------------

FROM builder AS release

# Release SHA for observability (Sentry/Logfire)
ARG RELEASE_SHA=development
RUN echo "${RELEASE_SHA}" > /.release

# Create non-root user for security
RUN useradd --no-create-home --no-log-init --shell /usr/sbin/nologin --uid 1000 appuser

WORKDIR /app

# Copy entrypoint script and make it executable (before switching to appuser)
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY . /app/

ENV DJP_PLUGINS_DIR=django_plugins

# Create dist directory for static files and give appuser ownership
RUN mkdir -p /app/dist && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--limit-max-requests", "1000", "--timeout-graceful-shutdown", "7"]
