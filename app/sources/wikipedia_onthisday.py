import hashlib
import json
import urllib.request

USER_AGENT = "curiosity-feed/0.1 (https://github.com/janghoyeol/curiosity-feed)"
BASE_URL = "https://en.wikipedia.org/api/rest_v1/feed/onthisday/all"


def fetch_onthisday_raw(month: int, day: int) -> dict:
    """위키백과 공식 REST API로 특정 월/일의 '오늘의 역사' 이벤트를 가져온다.

    한국어 위키백과는 이 피드를 제공하지 않아 영어판을 쓰고, 번역/질문화는
    Gate2(LLM) 단계에서 처리한다.

    httpx로 호출하면 위키백과 엣지에서 403이 뜨는데(라이브러리 TLS 핑거프린팅으로
    보임, UA 문제가 아니라 urllib/curl 등 다른 클라이언트는 같은 헤더로도 통과함),
    그래서 표준 라이브러리 urllib을 쓴다.
    """
    url = f"{BASE_URL}/{month:02d}/{day:02d}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_events(raw: dict) -> list[dict]:
    """원본 JSON에서 (external_id, text) 쌍만 뽑아낸다.

    external_id는 텍스트 해시라서, 매년 같은 날짜에 같은 역사적 사건이
    다시 와도 중복으로 잡힌다(Gate1의 source+external_id 중복 체크와 맞물림).
    """
    parsed = []
    for event in raw.get("events", []):
        text = (event.get("text") or "").strip()
        if not text:
            continue
        external_id = hashlib.sha256(text.encode("utf-8")).hexdigest()
        parsed.append({"external_id": external_id, "text": text})
    return parsed
