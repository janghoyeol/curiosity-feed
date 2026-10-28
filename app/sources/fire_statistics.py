import os
import time
from collections import Counter

import httpx

BASE_URL = "https://api.odcloud.kr/api/15060386/v1/uddi:fa73f7a3-dfa1-4b0a-ada8-dcd8333ba9e4"
PAGE_SIZE = 1000
MAX_RETRIES_PER_PAGE = 3


def _fetch_page(page: int, service_key: str) -> list[dict]:
    """한 페이지를 가져온다. 이 소스는 연결이 간헐적으로 끊기는 경우가 있어 재시도한다."""
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES_PER_PAGE):
        try:
            response = httpx.get(
                BASE_URL,
                params={"page": page, "perPage": PAGE_SIZE, "returnType": "JSON", "serviceKey": service_key},
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except httpx.TransportError as error:
            last_error = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"페이지 {page} 요청이 {MAX_RETRIES_PER_PAGE}번 모두 실패함") from last_error


def fetch_all_fire_records(service_key: str | None = None) -> list[dict]:
    """공공데이터포털 '소방청_연간화재통계' Open API에서 전체 화재 기록을 페이지네이션으로 가져온다.

    원재료가 완성된 문장이 아니라 개별 화재 사건 로우(3만여 건)라서, 여기서는
    원본 수집만 하고 문장화(흥미로운 사실 추출)는 compute_insights에서 따로 한다.
    """
    service_key = service_key or os.environ.get("DATA_GO_KR_FIRE_SERVICE_KEY")
    if not service_key:
        raise RuntimeError("DATA_GO_KR_FIRE_SERVICE_KEY 환경변수가 설정되어 있지 않습니다.")

    records: list[dict] = []
    page = 1
    while True:
        batch = _fetch_page(page, service_key)
        records.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        page += 1
    return records


def _amount(record: dict, key: str) -> int:
    try:
        return int(record.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _year_of(record: dict) -> str | None:
    date_str = record.get("일시")
    if not date_str or len(date_str) < 4:
        return None
    return date_str[:4]


def _hour_of(record: dict) -> int | None:
    date_str = record.get("일시")
    if not date_str or len(date_str) < 13:
        return None
    try:
        return int(date_str[11:13])
    except ValueError:
        return None


def compute_insights(records: list[dict]) -> list[dict]:
    """화재 기록 리스트에서 "흥미로운 사실" 문장 몇 개를 뽑아낸다.

    같은 연도 데이터로 다시 돌려도 같은 external_id가 나오게 해서,
    재집계해도 Gate1이 중복으로 걸러주게 한다.
    """
    if not records:
        return []

    year_counts = Counter(y for y in (_year_of(r) for r in records) if y)
    year = year_counts.most_common(1)[0][0] if year_counts else "unknown"

    total = len(records)
    insights = []

    causes = Counter(r.get("발화요인대분류") for r in records if r.get("발화요인대분류"))
    if causes:
        cause, count = causes.most_common(1)[0]
        pct = round(count / total * 100, 1)
        insights.append(
            {
                "external_id": f"fire:{year}:top_cause",
                "text": f"{year}년 한국에서 발생한 화재 {total:,}건 중 가장 많은 원인은 "
                f"'{cause}'였으며, 전체의 {pct}%를 차지했다.",
            }
        )

    regions = Counter(r.get("시도") for r in records if r.get("시도"))
    if regions:
        region, count = regions.most_common(1)[0]
        insights.append(
            {
                "external_id": f"fire:{year}:top_region",
                "text": f"{year}년 화재가 가장 많이 발생한 시도는 {region}로, 총 {count:,}건이 발생했다.",
            }
        )

    damage_by_type: Counter = Counter()
    for r in records:
        fire_type = r.get("화재유형")
        if fire_type:
            damage_by_type[fire_type] += _amount(r, "재산피해소계")
    if damage_by_type:
        fire_type, amount = damage_by_type.most_common(1)[0]
        insights.append(
            {
                "external_id": f"fire:{year}:worst_damage_type",
                "text": f"{year}년 화재유형 중 재산피해 총액이 가장 큰 유형은 '{fire_type}'로, "
                f"총 {amount:,}원의 피해가 발생했다.",
            }
        )

    hours = Counter(h for h in (_hour_of(r) for r in records) if h is not None)
    if hours:
        hour, count = hours.most_common(1)[0]
        pct = round(count / total * 100, 1)
        insights.append(
            {
                "external_id": f"fire:{year}:peak_hour",
                "text": f"{year}년 화재는 하루 중 {hour}시에 가장 많이 발생했다 (전체의 {pct}%).",
            }
        )

    worst_fire = max(records, key=lambda r: _amount(r, "재산피해소계"), default=None)
    if worst_fire and _amount(worst_fire, "재산피해소계") > 0:
        amount = _amount(worst_fire, "재산피해소계")
        insights.append(
            {
                "external_id": f"fire:{year}:worst_single_fire",
                "text": f"{year}년 {worst_fire.get('시도', '')} {worst_fire.get('시_군_구', '')}에서 "
                f"발생한 화재는 재산피해액이 {amount:,}원으로 그해 가장 큰 단일 화재였다.",
            }
        )

    return insights
