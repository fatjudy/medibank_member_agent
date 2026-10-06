"""The agent's control flow, with every step replaced by a fake so no API is called."""

import pytest

import src.agent as agent_module
from src.agent import Agent
from src.models import Answer, Citation, DocName, EscalationCategory, EscalationDecision
from tests.conftest import make_retrieved

GOOD_ANSWER = Answer(
    text="12 months.", confidence=0.9,
    citations=[Citation(doc=DocName.MEMBER_GUIDE, page=21, section="Having a baby?")],
)
OK = EscalationDecision(escalate=False)


class FakeRetriever:
    def __init__(self):
        self.calls = 0

    def retrieve(self, question, top_k=5):
        self.calls += 1
        return [make_retrieved(1)]


@pytest.fixture
def agent(monkeypatch, tmp_path):
    monkeypatch.setattr(agent_module, "LOG_PATH", tmp_path / "log.jsonl")
    monkeypatch.setattr(agent_module, "check_question", lambda q: OK)
    monkeypatch.setattr(agent_module, "check_retrieval", lambda chunks: OK)
    monkeypatch.setattr(agent_module, "check_answer", lambda a: OK)
    monkeypatch.setattr(agent_module, "generate_answer", lambda q, chunks: GOOD_ANSWER)
    monkeypatch.setattr(Agent, "rewrite_followup", lambda self, q: q)
    return Agent(retriever=FakeRetriever())


def test_happy_path_returns_answer_with_sources(agent):
    response = agent.handle("What is the waiting period for pregnancy?")
    assert not response.escalation.escalate
    assert response.answer == GOOD_ANSWER and len(response.sources) == 1


def test_escalation_before_retrieval_skips_search_and_answering(agent, monkeypatch):
    decision = EscalationDecision(escalate=True, category=EscalationCategory.ACCOUNT_SPECIFIC, reason="claim")
    monkeypatch.setattr(agent_module, "check_question", lambda q: decision)
    monkeypatch.setattr(agent_module, "generate_answer", lambda q, c: pytest.fail("should not answer"))

    response = agent.handle("Why was my claim rejected?")

    assert response.escalation == decision
    assert response.answer is None
    assert response.message == agent_module.MESSAGES[EscalationCategory.ACCOUNT_SPECIFIC]
    assert agent.retriever.calls == 0


def test_low_confidence_answer_is_escalated(agent, monkeypatch):
    low = EscalationDecision(escalate=True, category=EscalationCategory.LOW_CONFIDENCE, reason="low")
    monkeypatch.setattr(agent_module, "check_answer", lambda a: low)
    response = agent.handle("How much does Gold cover cost?")
    assert response.escalation.category == EscalationCategory.LOW_CONFIDENCE and response.answer is None


def test_history_keeps_only_the_last_three_turns(agent):
    for i in range(5):
        agent.handle(f"question {i}")
    assert len(agent.history) == 6
    assert agent.history[0]["content"] == "question 2"


def test_each_turn_is_logged(agent):
    agent.handle("q1")
    agent.handle("q2")
    assert len(agent_module.LOG_PATH.read_text(encoding="utf-8").splitlines()) == 2
