"""Offline study messages: a user-provided example and newly written encouragement.
These messages are not quotations attributed to historical figures.
"""
import datetime
import hashlib
from sourced_quotes import SOURCED_QUOTES

MESSAGES = (
    "실력은 정답을 확인하는 것으로 커지는 것이 아니라,\n틀린 이유를 이해하는 것으로부터 커진다.",
    "틀린 문제를 다시 바라보는 순간부터,\n그 문제는 실패가 아니라 배울 기회가 된다.",
    "막힌 문제는 실력의 끝이 아니라,\n다음에 배울 내용을 알려주는 표시다.",
    "오늘 이해한 한 줄이,\n내일 풀어낼 문제의 출발점이 된다.",
    "외운 답보다 오래 남는 것은,\n왜 그 답이 나오는지 스스로 설명해 본 경험이다.",
    "한 번에 풀리지 않아도 괜찮다.\n다시 생각해 본 시간도 공부에 쌓인다.",
    "많은 문제를 넘기는 것보다,\n한 문제에서 무엇을 배웠는지 아는 것이 중요하다.",
    "모른다고 말할 수 있어야,\n정확히 알아가는 공부를 시작할 수 있다.",
    "어제 틀린 문제를 오늘 스스로 풀었다면,\n그만큼 분명히 앞으로 나아간 것이다.",
    "다른 사람의 속도보다,\n어제의 내가 놓쳤던 것을 오늘 알아보자.",
    "답지를 덮고 다시 풀어보자.\n이해한 것과 익숙해진 것을 구별할 수 있다.",
    "계획이 완벽해질 때를 기다리기보다,\n지금 할 수 있는 작은 공부부터 시작하자.",
    "스스로 던진 좋은 질문 하나가,\n대충 넘긴 여러 페이지보다 깊은 공부가 된다.",
    "쉬운 문제에서도 이유를 묻고,\n어려운 문제에서도 배울 한 가지를 찾아보자.",
    "공식이 기억나지 않을 때,\n그 공식이 만들어진 이유로 돌아가 보자.",
    "알 것 같은 느낌에서 멈추지 말고,\n내 말로 설명할 수 있는지 확인해 보자.",
    "오늘의 목표는 모든 것을 아는 것이 아니라,\n어제 몰랐던 한 가지를 분명히 아는 것이다.",
    "같은 실수가 보이면 자신을 탓하기보다,\n어느 생각에서 길이 바뀌었는지 찾아보자.",
    "풀리지 않는 문제에는 잠시 거리를 두어도 괜찮다.\n쉬고 돌아오는 것도 공부를 이어가는 방법이다.",
    "정리한 노트의 양보다,\n다시 꺼내 쓸 수 있는 이해를 하나 더 만들자.",
    "배운 것을 친구에게 설명해 보면,\n내가 아는 부분과 더 배울 부분이 선명해진다.",
    "집중이 흐트러진 하루에도,\n다시 책을 펴는 순간부터 시작할 수 있다.",
    "어려운 문제를 만났다면 먼저 조건을 천천히 읽자.\n첫걸음은 빠른 계산보다 정확한 이해다.",
    "오늘 남긴 오답의 이유가,\n다음번에 같은 길을 헤매지 않게 도와준다.",
    "질문하고 도움을 구하는 것도,\n스스로 공부를 이어가는 힘이다.",
    "많이 풀었다는 기록에 더해,\n무엇을 새로 이해했는지도 남겨보자.",
    "아직 풀지 못했다는 말 속에는,\n앞으로 풀어갈 가능성이 남아 있다.",
    "매번 잘할 필요는 없다.\n다시 살펴보고 조금씩 고쳐갈 수 있으면 된다.",
    "긴 공부의 시작은 거창하지 않아도 된다.\n지금 눈앞의 한 문장을 이해하는 것부터 해보자.",
    "틀린 답을 지우기 전에,\n그 답을 고른 내 생각부터 읽어보자.",
)


ALL_QUOTES = tuple({"text": text, "kind": "study_message"} for text in MESSAGES) + SOURCED_QUOTES


def quote_for_day(day=None, cfg=None):
    """Choose locally and reproducibly by date; opening a preview never fetches quotes."""
    day = day or datetime.date.today()
    cfg = cfg or {}
    index = cfg.get("quote_index", -1)
    if (cfg.get("quote_date") == day.isoformat() and type(index) is int
            and 0 <= index < len(ALL_QUOTES)):
        return dict(ALL_QUOTES[index])
    seed = hashlib.sha256(("schoolunch-study-v3:" + day.isoformat()).encode()).digest()
    return dict(ALL_QUOTES[int.from_bytes(seed[:8], "big") % len(ALL_QUOTES)])
