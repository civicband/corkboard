"""Tests for API key authentication."""

import pytest

from django_plugins.api_key_auth import (
    extract_api_key,
    is_json_endpoint,
    make_401_response,
)


class TestIsJsonEndpoint:
    """Test JSON endpoint detection."""

    def test_json_endpoint(self):
        assert is_json_endpoint("/meetings/minutes.json") is True

    def test_query_json_endpoint(self):
        assert is_json_endpoint("/meetings/-/query.json") is True

    def test_html_endpoint(self):
        assert is_json_endpoint("/meetings/minutes") is False

    def test_html_query_endpoint(self):
        assert is_json_endpoint("/meetings/-/query") is False

    def test_json_in_path_but_not_extension(self):
        assert is_json_endpoint("/meetings/json/minutes") is False


class TestExtractApiKey:
    """Test API key extraction from requests."""

    def test_bearer_token(self):
        headers = [(b"authorization", b"Bearer test_key_123")]
        assert extract_api_key(headers, b"") == "test_key_123"

    def test_bearer_token_case_insensitive(self):
        headers = [(b"authorization", b"bearer test_key_123")]
        assert extract_api_key(headers, b"") == "test_key_123"

    def test_x_api_key_header(self):
        headers = [(b"x-api-key", b"test_key_456")]
        assert extract_api_key(headers, b"") == "test_key_456"

    def test_query_param(self):
        headers = []
        query = b"api_key=test_key_789&other=value"
        assert extract_api_key(headers, query) == "test_key_789"

    def test_header_takes_precedence_over_query(self):
        headers = [(b"authorization", b"Bearer header_key")]
        query = b"api_key=query_key"
        assert extract_api_key(headers, query) == "header_key"

    def test_no_key(self):
        headers = [(b"content-type", b"application/json")]
        assert extract_api_key(headers, b"") is None

    def test_empty_request(self):
        assert extract_api_key([], b"") is None


class TestMake401Response:
    """Test 401 response generation."""

    def test_response_body(self):
        body, headers = make_401_response()
        assert b"API key required" in body
        assert b"https://civic.observer/api-keys" in body

    def test_response_headers(self):
        body, headers = make_401_response()
        header_dict = {k.decode(): v.decode() for k, v in headers}
        assert header_dict["content-type"] == "application/json"
        assert header_dict["content-length"] == str(len(body))


@pytest.mark.asyncio
class TestValidateApiKey:
    """Test API key validation (with stubbed civic.observer)."""

    @pytest.fixture(autouse=True)
    def reset_redis_client(self):
        """Reset Redis client between tests."""
        from django_plugins import api_key_auth

        api_key_auth._redis_client = None
        yield
        api_key_auth._redis_client = None

    @pytest.fixture
    def fake_redis(self):
        """Create a fake Redis client for testing."""
        import fakeredis.aioredis

        return fakeredis.aioredis.FakeRedis()

    async def test_dev_key_valid_in_debug_mode(self, settings, fake_redis):
        from django_plugins.api_key_auth import set_redis_client, validate_api_key

        set_redis_client(fake_redis)
        settings.DEBUG = True
        # Dev keys are accepted by the stub in DEBUG mode
        result = await validate_api_key("dev_test_key", "alameda.ca")
        assert result["valid"] is True
        assert result["org_id"] == "dev"

    async def test_dev_key_rejected_in_production(self, settings, fake_redis):
        from django_plugins.api_key_auth import set_redis_client, validate_api_key

        set_redis_client(fake_redis)
        settings.DEBUG = False
        # Dev keys are rejected when DEBUG=False
        result = await validate_api_key("dev_test_key", "alameda.ca")
        assert result["valid"] is False

    async def test_invalid_key(self, settings, fake_redis):
        from django_plugins.api_key_auth import set_redis_client, validate_api_key

        set_redis_client(fake_redis)
        settings.DEBUG = True
        # Non-dev keys are rejected by the stub
        result = await validate_api_key("invalid_key", "alameda.ca")
        assert result["valid"] is False

    async def test_valid_key_is_cached(self, settings, fake_redis):
        from django_plugins.api_key_auth import (
            _cache_key,
            set_redis_client,
            validate_api_key,
        )

        set_redis_client(fake_redis)
        settings.DEBUG = True

        # First call
        await validate_api_key("dev_test_key", "alameda.ca")

        # Check it was cached
        cached = await fake_redis.get(_cache_key("dev_test_key"))
        assert cached is not None
        assert b"valid" in cached
        assert b"true" in cached.lower()

    async def test_invalid_key_is_cached(self, settings, fake_redis):
        from django_plugins.api_key_auth import (
            _cache_key,
            set_redis_client,
            validate_api_key,
        )

        set_redis_client(fake_redis)
        settings.DEBUG = True

        # Call with invalid key
        await validate_api_key("invalid_key", "alameda.ca")

        # Check it was cached
        cached = await fake_redis.get(_cache_key("invalid_key"))
        assert cached is not None
        assert b"valid" in cached
        assert b"false" in cached.lower()
