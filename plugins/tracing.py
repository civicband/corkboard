"""Logfire tracing utilities for Datasette plugins."""

import asyncio
import functools

import logfire


def trace_plugin(func):
    """Wrap plugin functions with Logfire spans.

    Creates a span named 'plugin:<module>.<function>' for timing and error tracking.
    Works with both sync and async functions.
    """
    plugin_name = func.__module__.split(".")[-1]
    span_name = f"plugin:{plugin_name}.{func.__name__}"

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        with logfire.span(span_name):
            return await func(*args, **kwargs)

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        with logfire.span(span_name):
            return func(*args, **kwargs)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
