import html
import os
import re

import httpx

API_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
DEFAULT_QUERIES = ["과학", "건강", "우주", "환경", "역사"]

_TAG_PATTERN = re.compile(r"<[^>]+>")


def _clean_text(raw: str) -> str:
    """응답의 title/description엔 검색어를 감싸는 <b> 태그와 HTML 엔티티가 섞여 있어 정리한다.

    엔티티를 먼저 풀고 태그를 벗겨내야, 혹시 &lt;b&gt;처럼 이중으로 인코딩된
    경우도 태그가 안 남는다.
    """
    return _TAG_PATTERN.sub("", html.unescape(raw or "")).strip()


def fetch_news(
    query: str,
    display: int = 10,
    sort: str = "date",
    client_id: str | None = None,
    client_secret: str | None = None,
) -> list[dict]:
    """NAVER API HUB 뉴스 검색으로 원본 결과(items)를 가져온다."""
    client_id = client_id or os.environ.get("NAVER_CLIENT_ID")
    client_secret = client_secret or os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 설정되어 있지 않습니다.")

    response = httpx.get(
        API_URL,
        params={"query": query, "display": display, "sort": sort, "format": "json"},
        headers={
            "X-NCP-APIGW-API-KEY-ID": client_id,
            "X-NCP-APIGW-API-KEY": client_secret,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("items", [])


def parse_items(raw_items: list[dict]) -> list[dict]:
    """<b> 태그/HTML 엔티티를 정리하고 (external_id, text) 쌍만 뽑아낸다.

    external_id는 기사 링크로 둔다 — 같은 기사가 다른 검색어로 다시 걸려도
    Gate1의 중복 체크(source+external_id)가 그대로 걸러준다.
    """
    parsed = []
    for item in raw_items:
        link = item.get("link") or item.get("originallink")
        title = _clean_text(item.get("title", ""))
        description = _clean_text(item.get("description", ""))
        if not link or not title:
            continue
        text = f"{title} - {description}" if description else title
        parsed.append({"external_id": link, "text": text})
    return parsed


def fetch_and_parse(queries: list[str] | None = None, display: int = 10) -> list[dict]:
    queries = queries if queries is not None else DEFAULT_QUERIES
    all_items: list[dict] = []
    for query in queries:
        all_items.extend(parse_items(fetch_news(query, display=display)))
    return all_items
