"""Shared test fixtures. Nothing here calls the Claude API."""

import pytest

from src.chunking import CHUNKS_PATH, build_chunks, save_chunks
from src.models import Chunk, DocName, RetrievedChunk


@pytest.fixture(scope="session")
def retriever():
    """The real retriever, built from the real PDFs (slow to load, so shared across tests)."""
    from src.retrieval import Retriever

    if not CHUNKS_PATH.exists():
        save_chunks(build_chunks())
    return Retriever()


def make_chunk(i: int = 1, doc: DocName = DocName.MEMBER_GUIDE, section: str = "Hospital Cover > Having a baby?") -> Chunk:
    return Chunk(chunk_id=f"{doc.value}-p{i}-{i:03d}", doc=doc, page=i, section=section, text=f"{section}\nText {i}")


def make_retrieved(i: int = 1, semantic: float = 0.5, **kwargs) -> RetrievedChunk:
    return RetrievedChunk(chunk=make_chunk(i, **kwargs), score=0.03, semantic_score=semantic)
