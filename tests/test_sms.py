from unittest.mock import Mock, patch

from messaging.sms import send_sms


def clear_sms_env(monkeypatch):
    for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"):
        monkeypatch.delenv(key, raising=False)


def test_missing_credentials_fails_closed(monkeypatch):
    clear_sms_env(monkeypatch)
    result = send_sms("+2348012345678", "SILKOUS test")
    assert not result.sent
    assert "not configured" in result.message


def test_invalid_destination_fails_closed(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15005550006")
    result = send_sms("08012345678", "SILKOUS test")
    assert not result.sent
    assert "E.164" in result.message


def test_empty_message_fails_closed(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15005550006")
    result = send_sms("+2348012345678", "   ")
    assert not result.sent
    assert "empty" in result.message


@patch("messaging.sms.requests.post")
def test_successful_provider_acceptance(mock_post, monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15005550006")
    mock_post.return_value = Mock(status_code=201)
    result = send_sms("+2348012345678", "SILKOUS setup test")
    assert result.sent
    assert "accepted by provider" in result.message
    mock_post.assert_called_once()
    assert mock_post.call_args.kwargs["timeout"] == 12


@patch("messaging.sms.requests.post")
def test_provider_rejection_is_not_reported_as_sent(mock_post, monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-token")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15005550006")
    mock_post.return_value = Mock(status_code=400)
    result = send_sms("+2348012345678", "SILKOUS setup test")
    assert not result.sent
    assert "HTTP 400" in result.message
