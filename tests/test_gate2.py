from app.gate2 import ScoredQuestion, generate_question, run_gate2, score_question


def test_generate_question_strips_quotes_and_whitespace():
    def fake_llm_call(prompt, **kwargs):
        return '"문어는 왜 심장이 3개나 필요할까?"\n'

    question = generate_question("문어는 심장이 3개다", llm_call=fake_llm_call)

    assert question == "문어는 왜 심장이 3개나 필요할까?"


def test_generate_question_includes_raw_text_in_prompt():
    captured = {}

    def fake_llm_call(prompt, **kwargs):
        captured["prompt"] = prompt
        return "질문"

    generate_question("독특한 원재료 텍스트", llm_call=fake_llm_call)

    assert "독특한 원재료 텍스트" in captured["prompt"]


def test_score_question_parses_json_response():
    def fake_llm_call(prompt, **kwargs):
        return '{"score": 4.0, "reason": "누구에게나 같은 답이 적용되는 사실형 질문"}'

    result = score_question("엔진오일 교환 주기는 킬로수 기준인가요?", llm_call=fake_llm_call)

    assert isinstance(result, ScoredQuestion)
    assert result.score == 4.0
    assert result.reason == "누구에게나 같은 답이 적용되는 사실형 질문"


def test_score_question_passes_json_response_format_flag():
    captured = {}

    def fake_llm_call(prompt, **kwargs):
        captured["kwargs"] = kwargs
        return '{"score": 1.0, "reason": "이유"}'

    score_question("질문", llm_call=fake_llm_call)

    assert captured["kwargs"]["response_format_json"] is True


def test_run_gate2_combines_generation_and_scoring():
    responses = iter(["문어는 왜 심장이 3개나 필요할까?", '{"score": 4.5, "reason": "사실형 질문"}'])

    def fake_llm_call(prompt, **kwargs):
        return next(responses)

    result = run_gate2("문어는 심장이 3개다", llm_call=fake_llm_call)

    assert result.question == "문어는 왜 심장이 3개나 필요할까?"
    assert result.score == 4.5
    assert result.reason == "사실형 질문"
