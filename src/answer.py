"""Generate a grounded, cited answer from retrieved chunks using Claude."""

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.models import Answer, Citation, RetrievedChunk

load_dotenv()

MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """You are a member support assistant for Medibank, an Australian private health insurer.

You answer members' questions using ONLY the numbered source extracts provided with each question, \
which come from Medibank's Fund Rules and Member Guide.

Rules:
- Base every statement on the extracts. Do not use outside knowledge about health insurance.
- If the extracts do not contain the answer, set found_in_sources to false and say briefly that you \
could not find it in the documents. Do not guess.
- Cite the extracts you used by their numbers in source_ids.
- Give general information only, never medical or financial advice.

How to write the answer (this is a chat, so be brief):
- Start with a direct answer in the first sentence (e.g. "Yes, ...", "Usually, ...", "No, ...", \
"It's 12 months.").
- Then add only the details the member needs to act on it. Do not explain related rules they did not \
ask about.
- Keep the whole answer under 60 words: at most 3 short sentences, or one sentence plus up to 4 short \
bullet points when listing steps or conditions.
- If the answer depends on their specific cover, end with one short line telling them to check their \
Cover Summary. Mention it once only.
- Plain, friendly English, not legal language. Do not repeat the question."""


class LLMAnswer(BaseModel):
    """The JSON shape Claude must return. Citations are mapped from source_ids by our code."""
    answer: str
    source_ids: list[int] = Field(description="Numbers of the extracts the answer is based on.")
    found_in_sources: bool = Field(description="False if the extracts do not answer the question.")
    confidence: float = Field(description="0 to 1: how fully the extracts support the answer.")


_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def format_sources(chunks: list[RetrievedChunk]) -> str:
    """Number each chunk so Claude can cite it as [1], [2], ..."""
    blocks = []
    for i, rc in enumerate(chunks, start=1):
        c = rc.chunk
        blocks.append(f"[{i}] ({c.doc.value}, page {c.page}, {c.section})\n{c.text}")
    return "\n\n".join(blocks)


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict] | None = None,
) -> Answer:
    """Ask Claude to answer from the chunks; return a validated Answer with real citations."""
    user_content = f"Source extracts:\n\n{format_sources(chunks)}\n\nMember question: {question}"
    messages = [*(history or []), {"role": "user", "content": user_content}]

    response = get_client().beta.messages.parse(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=messages,
        output_config={"effort": "low"},
        output_format=LLMAnswer,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return Answer(text="Sorry, I couldn't answer that. Please contact Medibank on 132 331.", confidence=0.0)

    out = response.parsed_output
    if not out.found_in_sources:
        return Answer(text=out.answer, confidence=0.0)

    # Map source numbers back to real chunks: citations come from our data, not from the model.
    used = [chunks[i - 1].chunk for i in out.source_ids if 1 <= i <= len(chunks)]
    unique = {(c.doc, c.page, c.section): c for c in used}
    citations = [Citation(doc=c.doc, page=c.page, section=c.section) for c in unique.values()]

    return Answer(text=out.answer, citations=citations, confidence=min(max(out.confidence, 0.0), 1.0))


if __name__ == "__main__":
    from src.retrieval import Retriever

    retriever = Retriever()
    for q in [
        "What is the waiting period for pregnancy?",
        "Can I suspend my membership while I travel overseas?",
        "Does Medibank cover pet insurance?",
    ]:
        answer = generate_answer(q, retriever.retrieve(q))
        print(f"\nQ: {q}\nA: {answer.text}\nconfidence: {answer.confidence}")
        for c in answer.citations:
            print(f"   - {c.doc.value}, p{c.page}, {c.section}")