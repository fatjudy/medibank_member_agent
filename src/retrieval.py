"""Hybrid retrieval over chunks: BM25 (keywords) + embeddings (meaning), fused with RRF."""

import re

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from src.chunking import INDEX_DIR, load_chunks
from src.models import Chunk, RetrievedChunk

EMBED_MODEL = "all-MiniLM-L6-v2"
EMBEDDINGS_PATH = INDEX_DIR / "embeddings.npy"
RRF_K = 60

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from", "how",
    "i", "if", "in", "is", "it", "my", "of", "on", "or", "the", "to", "what", "when", "which",
    "who", "will", "with", "you", "your",
}


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens without stopwords, for BM25."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


class Retriever:
    """Loads chunks once and answers hybrid search queries."""

    def __init__(self) -> None:
        self.chunks: list[Chunk] = load_chunks()
        self.bm25 = BM25Okapi([tokenize(c.text) for c in self.chunks])
        self.model = SentenceTransformer(EMBED_MODEL)
        self.vectors = self._load_or_build_vectors()

    def _load_or_build_vectors(self) -> np.ndarray:
        """Reuse cached embeddings if they match the current chunks, else rebuild."""
        if EMBEDDINGS_PATH.exists():
            vectors = np.load(EMBEDDINGS_PATH)
            if len(vectors) == len(self.chunks):
                return vectors
        vectors = self.model.encode([c.text for c in self.chunks], normalize_embeddings=True)
        np.save(EMBEDDINGS_PATH, vectors)
        return vectors

    def bm25_ranking(self, question: str) -> list[int]:
        """Chunk indices ordered by BM25 score, best first."""
        scores = self.bm25.get_scores(tokenize(question))
        return list(np.argsort(scores)[::-1])

    def semantic_scores(self, question: str) -> np.ndarray:
        """Cosine similarity of the question to every chunk."""
        query = self.model.encode([question], normalize_embeddings=True)[0]
        return self.vectors @ query

    def retrieve(self, question: str, top_k: int = 5, pool: int = 20) -> list[RetrievedChunk]:
        """Top-k chunks by Reciprocal Rank Fusion of the BM25 and semantic rankings."""
        semantic = self.semantic_scores(question)
        rankings = [
            self.bm25_ranking(question)[:pool],
            list(np.argsort(semantic)[::-1][:pool]),
        ]
        rrf: dict[int, float] = {}
        for ranking in rankings:
            for rank, idx in enumerate(ranking):
                rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)

        best = sorted(rrf, key=rrf.get, reverse=True)[:top_k]
        return [
            RetrievedChunk(chunk=self.chunks[i], score=rrf[i], semantic_score=float(semantic[i]))
            for i in best
        ]


if __name__ == "__main__":
    retriever = Retriever()
    for q in [
        "What is the waiting period for pregnancy?",
        "Can I claim physio on extras?",
        "How do I suspend my membership if I travel overseas?",
        "Is ambulance covered?",
        "What is a pre-existing condition?",
        "What's the weather in Melbourne?",
    ]:
        print(f"\nQ: {q}")
        for r in retriever.retrieve(q, top_k=3):
            print(f"  {r.score:.4f}  sem={r.semantic_score:.2f}  p{r.chunk.page:<3} {r.chunk.section[:80]}")