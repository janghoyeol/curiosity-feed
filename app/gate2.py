import json
from dataclasses import dataclass
from typing import Callable

from app.llm.groq_client import chat_completion

GENERATION_PROMPT = """다음 사실에서, 사람들이 "오 그거 궁금한데?"라고 느낄 만한
핵심 포인트(의외의 인과관계, 반직관적인 숫자, 기록·비교, 왜 그런 일이
일어났는지)를 찾아 한국어 질문과 그 질문에 대한 답을 만들어라.

중요한 제약:
- 질문자 개인의 상황이나 선택(예산, 소유 제품, 개인적 취향)에 답이 좌우되면
  안 된다. 누구에게나 같은 답이 적용되는 사실형 질문이어야 한다.
- 단순히 "언제/어디서/누가 했는지"를 그대로 되묻지 마라. 사실 안에 있는
  "왜/어떻게/얼마나 대단한지"를 찾아 그 질문으로 만들어라.
- 질문과 답 모두 사실에 없는 내용을 지어내지 마라.
- 답은 사실에 있는 내용만으로 2~3문장 이내로 간결하게 설명하라.
- 원재료가 영어 등 다른 언어로 되어 있어도 질문과 답은 반드시 한국어로
  작성하라.

예시:
- 원재료: "2023년 럭비 월드컵 결승전은 마르세유 스타드 경기장에서 열렸다."
  → "어디서 열렸나요?"는 나쁜 질문(단순 사실 확인). 왜/얼마나 정보가 없으면
  좋은 질문을 만들기 어려운 소재라는 뜻이다.
- 원재료: "허리케인 멜리사는 북대서양에서 상륙한 역대 가장 강력한 허리케인으로
  기록됐다." → 질문: "멜리사는 왜 북대서양 역대 최강 허리케인으로 기록됐을까?"
  답: "멜리사가 북대서양에 상륙할 당시의 강도가 지금까지 관측된 어떤
  허리케인보다 강력했기 때문이다." (기록·비교라는 흥미 포인트를 살림)

사실: "{raw_text}"

다음 JSON 형식으로만 답하라. 다른 설명은 쓰지 마라.
{{"question": "...", "answer": "..."}}"""

SCORING_PROMPT = """다음 질문이 "평소엔 궁금하지 않았지만, 보는 순간 궁금해지는
질문"으로서 얼마나 흥미로운지 0~5점으로 평가하라.

핵심 기준: 질문자와 전혀 상관없는 사람이 이 질문만 보고 "오 그거 궁금한데?"라고
느낄지, "그래서 어쩌라고?"라고 느낄지로 판단하라.

예시로 구분:
- "차 사려는데 K5랑 아반떼 중 뭐가 나을까요?" → 0점. 답이 질문자의 예산·용도에만
  맞춰진 개인 선택이라 남이 보면 "그래서 어쩌라고"
- "엔진오일 교환 주기는 킬로수 기준인가요, 기간 기준인가요?" → 통과 가능. 차종이나
  예산과 무관하게 누구에게나 같은 답이 적용되는 사실형 질문

5점: 보자마자 클릭하고 싶어지는, 반직관적이거나 구체적인 궁금증
3점: 평범하지만 나쁘지 않은 사실/정보성 질문
0점: 광고/공지, 개인 선택에 의존하는 질문, 특정 분야 내부자만 아는 질문,
     첨부 자료가 있어야 이해되는 질문 중 하나라도 해당

질문: "{question}"

다음 JSON 형식으로만 답하라. 다른 설명은 쓰지 마라.
{{"score": <0~5 숫자>, "reason": "<한 문장 이유>"}}"""


@dataclass
class QuestionAndAnswer:
    question: str
    answer: str


@dataclass
class ScoredQuestion:
    question: str
    answer: str
    score: float
    reason: str


def generate_question_and_answer(
    raw_text: str, llm_call: Callable[..., str] = chat_completion
) -> QuestionAndAnswer:
    response = llm_call(
        GENERATION_PROMPT.format(raw_text=raw_text),
        temperature=0.7,
        response_format_json=True,
    )
    parsed = json.loads(response)
    return QuestionAndAnswer(question=parsed["question"].strip(), answer=parsed["answer"].strip())


def score_question(question: str, llm_call: Callable[..., str] = chat_completion) -> tuple[float, str]:
    response = llm_call(
        SCORING_PROMPT.format(question=question),
        temperature=0.1,
        response_format_json=True,
    )
    parsed = json.loads(response)
    return float(parsed["score"]), parsed["reason"]


def run_gate2(raw_text: str, llm_call: Callable[..., str] = chat_completion) -> ScoredQuestion:
    qa = generate_question_and_answer(raw_text, llm_call=llm_call)
    score, reason = score_question(qa.question, llm_call=llm_call)
    return ScoredQuestion(question=qa.question, answer=qa.answer, score=score, reason=reason)
