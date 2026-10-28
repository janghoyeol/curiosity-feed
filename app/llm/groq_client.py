import json
import os
import re
import time

import httpx

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
MAX_RETRY_WAIT_SECONDS = 10.0

_RESET_PATTERN = re.compile(r"^(?:(?P<minutes>\d+(?:\.\d+)?)m)?(?P<seconds>\d+(?:\.\d+)?)s?$")


def parse_retry_wait_seconds(header_value: str | None, default: float = 5.0) -> float:
    """Groq의 'x-ratelimit-reset-tokens' 같은 헤더값("47.317s", "1m2.3s")을 초 단위로 변환한다.

    실제 리셋까지 남은 시간이 너무 길면(예: 분 단위) 요청 하나를 그만큼 블로킹시킬
    수 없으니 MAX_RETRY_WAIT_SECONDS로 캡을 둔다.
    """
    if not header_value:
        return default
    match = _RESET_PATTERN.match(header_value.strip())
    if not match:
        return default
    minutes = float(match.group("minutes") or 0.0)
    seconds = float(match.group("seconds") or 0.0)
    return min(minutes * 60 + seconds, MAX_RETRY_WAIT_SECONDS)


def chat_completion(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    response_format_json: bool = False,
) -> str:
    """Groq의 OpenAI 호환 chat completions 엔드포인트를 호출하고 응답 텍스트를 반환한다.

    무료 티어는 분당 토큰(TPM) 한도가 낮아 배치 처리 중 429가 자주 뜬다.
    한 번은 짧게 기다렸다가 재시도하고, 그래도 안 되면 그대로 에러를 올린다.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY 환경변수가 설정되어 있지 않습니다.")

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    if response_format_json:
        body["response_format"] = {"type": "json_object"}

    for attempt in range(2):
        response = httpx.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=body,
            timeout=30,
        )
        if response.status_code == 429 and attempt == 0:
            wait_seconds = parse_retry_wait_seconds(response.headers.get("x-ratelimit-reset-tokens"))
            time.sleep(wait_seconds)
            continue
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
