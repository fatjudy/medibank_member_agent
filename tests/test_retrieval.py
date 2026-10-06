from src.retrieval import tokenize


def test_tokenize_lowercases_and_drops_stopwords():
    assert tokenize("What is the waiting period for Pregnancy?") == ["waiting", "period", "pregnancy"]


def test_retrieve_returns_top_k_in_score_order(retriever):
    results = retriever.retrieve("What is the waiting period for pregnancy?", top_k=5)
    assert len(results) == 5
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_finds_the_right_section(retriever):
    sections = [r.chunk.section for r in retriever.retrieve("What is the waiting period for pregnancy?")]
    assert any("Having a baby" in s for s in sections)


def test_semantic_score_separates_on_topic_from_off_topic(retriever):
    on_topic = max(r.semantic_score for r in retriever.retrieve("Is ambulance covered?"))
    off_topic = max(r.semantic_score for r in retriever.retrieve("What's the weather in Melbourne tomorrow?"))
    assert on_topic > off_topic
