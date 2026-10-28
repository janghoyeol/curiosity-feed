from unittest.mock import Mock, patch

from app.llm.groq_client import chat_completion, parse_retry_wait_seconds


def test_parse_retry_wait_seconds_plain_seconds():
    assert parse_retry_wait_seconds("7.5s") == 7.5


def test_parse_retry_wait_seconds_minutes_and_seconds_capped():
    # 47m31.2s는 10초(MAX_RETRY_WAIT_SECONDS)로 캡핑되어야 함
    assert parse_retry_wait_seconds("47m31.2s") == 10.0


def test_parse_retry_wait_seconds_missing_header_uses_default():
    assert parse_retry_wait_seconds(None, default=3.0) == 3.0


def test_parse_retry_wait_seconds_unparseable_uses_default():
    assert parse_retry_wait_seconds("garbage", default=3.0) == 3.0


def _mock_response(status_code, json_body=None, headers=None):
    resp = Mock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = json_body or {}
    if status_code >= 400:
        import httpx

        def raise_for_status():
            raise httpx.HTTPStatusError("error", request=Mock(), response=resp)

        resp.raise_for_status.side_effect = raise_for_status
    else:
        resp.raise_for_status.return_value = None
    return resp


@patch("app.llm.groq_client.time.sleep")
@patch("app.llm.groq_client.httpx.post")
def test_chat_completion_retries_once_on_429_then_succeeds(mock_post, mock_sleep, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")

    rate_limited = _mock_response(429, headers={"x-ratelimit-reset-tokens": "2s"})
    success = _mock_response(200, json_body={"choices": [{"message": {"content": "답변"}}]})
    mock_post.side_effect = [rate_limited, success]

    result = chat_completion("프롬프트")

    assert result == "답변"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once_with(2.0)


def test_chat_completion_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    try:
        chat_completion("프롬프트")
        assert False, "RuntimeError가 발생해야 함"
    except RuntimeError:
        pass
