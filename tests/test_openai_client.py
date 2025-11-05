
from pwm.ai.openai_client import OpenAIClient

def test_openai_client_from_config_returns_none_without_api_key():
    """Test that from_config returns None when API key is missing."""
    config = {"openai": {}}
    client = OpenAIClient.from_config(config)
    assert client is None

def test_openai_client_from_config_with_minimal_config():
    """Test creating client with minimal config (just API key)."""
    config = {"openai": {"api_key": "sk-test123"}}
    client = OpenAIClient.from_config(config)

    assert client is not None
    assert client.api_key == "sk-test123"
    assert client.base_url == "https://api.openai.com/v1"
    assert client.model == "gpt-4o-mini"
    assert client.max_tokens == 500
    assert client.temperature == 0.7

def test_openai_client_from_config_with_full_config():
    """Test creating client with full config overrides."""
    config = {
        "openai": {
            "api_key": "sk-custom",
            "base_url": "https://custom.api.com/v1",
            "model": "gpt-4o",
            "max_tokens": 1000,
            "temperature": 0.5
        }
    }
    client = OpenAIClient.from_config(config)

    assert client is not None
    assert client.api_key == "sk-custom"
    assert client.base_url == "https://custom.api.com/v1"
    assert client.model == "gpt-4o"
    assert client.max_tokens == 1000
    assert client.temperature == 0.5

def test_openai_client_headers():
    """Test that headers are correctly formatted."""
    config = {"openai": {"api_key": "sk-test123"}}
    client = OpenAIClient.from_config(config)

    headers = client._headers()
    assert headers["Authorization"] == "Bearer sk-test123"
    assert headers["Content-Type"] == "application/json"
