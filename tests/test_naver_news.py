from app.sources.naver_news import parse_items


def test_parse_items_strips_literal_tags():
    # 실제 API 응답은 title/description에 검색어를 감싸는 <b> 태그가 literal로 들어있다
    raw_items = [
        {
            "title": "<b>커피</b> 하루 몇 잔이 적당할까",
            "originallink": "http://example.com/1",
            "link": "http://example.com/1",
            "description": "전문가들은 <b>커피</b>를 하루 3잔 이하로 권장한다",
            "pubDate": "Thu, 11 Jun 2026 19:03:00 +0900",
        }
    ]

    parsed = parse_items(raw_items)

    assert len(parsed) == 1
    assert parsed[0]["external_id"] == "http://example.com/1"
    assert "<b>" not in parsed[0]["text"]
    assert "커피 하루 몇 잔이 적당할까" in parsed[0]["text"]
    assert "전문가들은 커피를 하루 3잔 이하로 권장한다" in parsed[0]["text"]


def test_parse_items_unescapes_html_entities():
    raw_items = [{"title": "회사 &quot;내년 목표&quot; 발표", "link": "http://example.com/2"}]

    parsed = parse_items(raw_items)

    assert parsed[0]["text"] == '회사 "내년 목표" 발표'


def test_parse_items_skips_items_without_link_or_title():
    raw_items = [
        {"title": "", "link": "http://example.com/empty-title"},
        {"title": "링크 없는 기사"},
    ]

    assert parse_items(raw_items) == []


def test_parse_items_falls_back_to_originallink():
    raw_items = [{"title": "제목", "originallink": "http://example.com/orig"}]

    parsed = parse_items(raw_items)

    assert parsed[0]["external_id"] == "http://example.com/orig"
