"""Tests for the trace_plugin decorator."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest


class TestTracePluginDecorator:
    """Test trace_plugin decorator."""

    def test_sync_function_wrapped(self):
        """Sync functions get wrapped with span."""
        from plugins.tracing import trace_plugin

        @trace_plugin
        def my_sync_func():
            return "result"

        with patch("plugins.tracing.logfire") as mock_logfire:
            mock_span = MagicMock()
            mock_logfire.span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_logfire.span.return_value.__exit__ = MagicMock(return_value=False)

            result = my_sync_func()

            assert result == "result"
            mock_logfire.span.assert_called_once()
            # Span name should include module and function name
            span_name = mock_logfire.span.call_args[0][0]
            assert "my_sync_func" in span_name

    @pytest.mark.asyncio
    async def test_async_function_wrapped(self):
        """Async functions get wrapped with span."""
        from plugins.tracing import trace_plugin

        @trace_plugin
        async def my_async_func():
            return "async_result"

        with patch("plugins.tracing.logfire") as mock_logfire:
            mock_span = MagicMock()
            mock_logfire.span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_logfire.span.return_value.__exit__ = MagicMock(return_value=False)

            result = await my_async_func()

            assert result == "async_result"
            mock_logfire.span.assert_called_once()

    def test_exception_propagates(self):
        """Exceptions are recorded and re-raised."""
        from plugins.tracing import trace_plugin

        @trace_plugin
        def my_failing_func():
            raise ValueError("test error")

        with patch("plugins.tracing.logfire") as mock_logfire:
            mock_span = MagicMock()
            mock_logfire.span.return_value.__enter__ = MagicMock(return_value=mock_span)
            mock_logfire.span.return_value.__exit__ = MagicMock(return_value=False)

            with pytest.raises(ValueError, match="test error"):
                my_failing_func()

    def test_preserves_function_metadata(self):
        """Decorator preserves function name and docstring."""
        from plugins.tracing import trace_plugin

        @trace_plugin
        def documented_func():
            """This is the docstring."""
            pass

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is the docstring."
