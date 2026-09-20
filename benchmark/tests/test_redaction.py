import pytest
from benchmark.run_suite import redact_text


def test_redact_bearer_token():
    text = "Authorization: Bearer secret_token_1234567890_value"
    redacted = redact_text(text)
    assert "secret_token_1234567890_value" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_api_key_and_secrets():
    text = "api_key=my_secret_key_1234 and password = mypass"
    redacted = redact_text(text)
    assert "my_secret_key_1234" not in redacted
    assert "mypass" not in redacted


def test_redact_no_sensitive_data():
    text = "This is a normal log string with no tokens."
    redacted = redact_text(text)
    assert redacted == text
