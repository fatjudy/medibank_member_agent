"""The chat pipeline: escalation checks -> retrieval -> grounded answer, one ChatResponse per turn."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from src.answer import MODEL, generate_answer, get_client
from src.escalation import MESSAGES, check_answer, check_question, check_retrieval
from src.models import ChatResponse, EscalationDecision
from src.retrieval import Retriever

LOG_PATH = Path("logs/chat_log.jsonl")
MAX_HISTORY_TURNS = 3   # question/answer pairs kept for follow-up questions

REWRITE_PROMPT = """Rewrite the member's latest message as a standalone question that makes sense \
without the conversation, keeping their meaning. If it is already standalone, return it unchanged. \
Return only the question."""


class Agent:
    """Holds the retriever and conversation history, and answers one message at a time."""

    def __init__(self, retriever: Retriever | None = None) -> None:
        self.retriever = retriever or Retriever()
        self.history: list[dict] = []
        self.last_search_query = ""   # what was actually searched, for logging

    def rewrite_followup(self, question: str) -> str:
        """Turn 'what about extras?' into a full question using the recent conversation."""
        if not self.history:
            return question
        conversation = "\n".join(f"{m['role']}: {m['content']}" for m in self.history)
        response = get_client().messages.create(
            model=MODEL,
            max_tokens=1000,
            system=REWRITE_PROMPT,
            messages=[{"role": "user", "content": f"Conversation:\n{conversation}\n\nLatest message: {question}"}],
            output_config={"effort": "low"},
        )
        text = next((b.text for b in response.content if b.type == "text"), "").strip()
        return text or question

    def handle(self, question: str) -> ChatResponse:
        """Run one member message through the full pipeline."""
        start = time.perf_counter()
        standalone = self.rewrite_followup(question)

        response = self._run(standalone)

        self._remember(question, response.message)
        self._log(question, standalone, response, time.perf_counter() - start)
        return response

    def _run(self, question: str) -> ChatResponse:
        decision, search_query = check_question(question)
        self.last_search_query = ""
        if decision.escalate:
            return escalated(decision)

        # Search with the member's words plus the policy-term rewrite; answer the original question.
        self.last_search_query = f"{question} {search_query}".strip()
        chunks = self.retriever.retrieve(self.last_search_query)
        decision = check_retrieval(chunks)
        if decision.escalate:
            return escalated(decision, chunks)

        answer = generate_answer(question, chunks)
        decision = check_answer(answer)
        if decision.escalate:
            return escalated(decision, chunks)

        return ChatResponse(message=answer.text, answer=answer, escalation=decision, sources=chunks)

    def _remember(self, question: str, reply: str) -> None:
        self.history += [{"role": "user", "content": question}, {"role": "assistant", "content": reply}]
        self.history = self.history[-2 * MAX_HISTORY_TURNS:]

    def _log(self, question: str, standalone: str, response: ChatResponse, seconds: float) -> None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "time": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "standalone_question": standalone,
            "search_query": self.last_search_query,
            "escalated": response.escalation.escalate,
            "category": response.escalation.category.value,
            "reason": response.escalation.reason,
            "chunk_ids": [s.chunk.chunk_id for s in response.sources],
            "top_semantic_score": max((s.semantic_score for s in response.sources), default=None),
            "confidence": response.answer.confidence if response.answer else None,
            "seconds": round(seconds, 2),
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


def escalated(decision: EscalationDecision, chunks: list | None = None) -> ChatResponse:
    """Build a response that hands off to a human, using the fixed message for the category."""
    return ChatResponse(message=MESSAGES[decision.category], escalation=decision, sources=chunks or [])


if __name__ == "__main__":
    agent = Agent()
    for q in [
        "What is the waiting period for pregnancy?",
        "What about for extras like dental?",
        "Why was my last claim rejected?",
        "What does the Fund Rules say about using funds for lunar mining?",
    ]:
        r = agent.handle(q)
        status = f"ESCALATED: {r.escalation.category.value} ({r.escalation.reason})" if r.escalation.escalate else "answered"
        print(f"\nQ: {q}\n[{status}]\nA: {r.message}")
        if r.answer:
            for c in r.answer.citations:
                print(f"   - {c.doc.value}, p{c.page}, {c.section}")
    print(f"\nLog: {LOG_PATH}")