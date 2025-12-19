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

COPY pyproject.toml /tmp/pyproject.toml

RUN --mount=type=cache,target=/root/.cache,sharing=locked,id=pip \
    python -m pip install --upgrade pip uv

RUN --mount=type=cache,target=/root/.cache,sharing=locked,id=pip \
    python -m uv pip compile /tmp/pyproject.toml -o /tmp/requirements.txt

RUN --mount=type=cache,target=/root/.cache,sharing=locked,id=pip \
    python -m uv pip install --system --requirement /tmp/requirements.txt

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

COPY . /app/

ENV DJP_PLUGINS_DIR=django_plugins

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--limit-max-requests", "1000", "--timeout-graceful-shutdown", "7"]
