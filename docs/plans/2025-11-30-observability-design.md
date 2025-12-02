# Observability Design: Bugsink + Logfire Integration

## Overview

This design adds comprehensive observability to CivicBand using:
- **Bugsink** (Sentry-compatible) for error tracking
- **Logfire** for traces, metrics, and structured logging

## Goals

1. **Error Visibility**: Capture and track errors from both Django and Datasette
2. **Request Tracing**: Understand request flow through the hybrid Django/Datasette architecture
3. **Health Monitoring**: Track application health and performance metrics
4. **Release Tracking**: Associate errors and traces with specific deployments

## Architecture Decisions

### Single Sentry Init at ASGI Level

Rather than using `datasette-sentry` (which may not work correctly with our dynamic Datasette instance creation), we initialize Sentry once at the ASGI level. This wraps everything - Django, Datasette, and the routing middleware.

**Rationale**:
- Datasette instances are created dynamically per-subdomain
- Single init point ensures all errors are captured
- Simpler configuration and maintenance

### Logfire with Django Instrumentation

Logfire provides automatic Django instrumentation plus manual spans for Datasette requests.

**Configuration**:
- Production: Full Logfire telemetry
- Development (DEBUG=True): Console output only for easy debugging

### Release Tracking via .release File

The release SHA is baked into the Docker image at build time:
1. Deploy workflow passes `RELEASE_SHA` build arg
2. Dockerfile writes SHA to `/.release`
3. Application reads from `/.release` at startup

## Implementation Details

### Environment Variables

```bash
# Error tracking (Bugsink/Sentry)
SENTRY_DSN=https://...@bugsink.example.com/...
SENTRY_ENVIRONMENT=production  # or staging, development

# Logfire
LOGFIRE_TOKEN=...
```

### config/asgi.py Changes

```python
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

# Read release from baked file
def get_release():
    try:
        with open("/.release") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "development"

# Initialize Sentry if DSN is configured
sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        release=get_release(),
        traces_sample_rate=0.1,
    )

# Wrap application
application = SentryAsgiMiddleware(application)
```

### config/settings.py Changes

```python
import logfire

# Logfire configuration
if DEBUG:
    # Development: console output only
    logfire.configure(send_to_logfire=False)
else:
    # Production: full telemetry
    logfire_token = os.environ.get("LOGFIRE_TOKEN")
    if logfire_token:
        logfire.configure(token=logfire_token)
        logfire.instrument_django()
```

### django_plugins/datasette_by_subdomain.py Changes

Add manual span for Datasette requests:

```python
import logfire

async def __call__(self, scope, receive, send):
    # ... existing subdomain extraction ...

    with logfire.span(
        "datasette_request",
        subdomain=subdomain,
        path=scope.get("path", ""),
        method=scope.get("method", "GET"),
    ):
        # ... existing Datasette handling ...
```

### Dockerfile Changes

```dockerfile
ARG RELEASE_SHA=development
RUN echo "${RELEASE_SHA}" > /.release
```

### Deploy Workflow Changes

```yaml
- name: Build and deploy Django on VPS
  run: |
    ssh ... "
      docker build --no-cache \
        --build-arg RELEASE_SHA=${{ github.sha }} \
        -t corkboard-django:${{ github.sha }} . &&
      ...
    "
```

## Dependencies

Add to pyproject.toml:
```toml
"logfire[django]>=0.30.0",
```

Note: `sentry-sdk` is already a dependency.

## Removed Dependencies

Remove from pyproject.toml:
```toml
"datasette-sentry>=0.3.0",  # Not needed with ASGI-level Sentry
```

## Testing Considerations

- Tests should work without Sentry/Logfire configured
- Both integrations gracefully handle missing configuration
- No mocking needed for observability in unit tests

## Rollout Plan

1. Deploy with observability disabled (no env vars set)
2. Configure SENTRY_DSN and verify error capture
3. Configure LOGFIRE_TOKEN and verify traces
4. Monitor for any performance impact
