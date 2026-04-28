from ingestion.loader import load_file
from vectorstore.store import (
    setup_table,
    ingest_documents,
    similarity_search,
    get_chunk_count
)


def test_setup_table_runs_without_error():
    setup_table()


def test_csv_loads_correctly():
    docs = load_file("data/sample.csv")
    assert len(docs) > 0
    assert "product" in docs[0].page_content.lower()
    assert "source" in docs[0].metadata


def test_chunk_count_is_positive():
    count = get_chunk_count()
    assert count > 0


def test_similarity_search_returns_results():
    results = similarity_search("pharmacy sales", k=3)
    assert len(results) > 0
    assert len(results) <= 3


def test_similarity_search_has_scores():
    results = similarity_search("insulin northeast", k=3)
    for r in results:
        assert "similarity_score" in r.metadata
        assert 0.0 <= r.metadata["similarity_score"] <= 1.0


def test_similarity_finds_relevant_content():
    results = similarity_search("insulin northeast sales", k=5)
    contents = [r.page_content.lower() for r in results]
    assert any(
        "insulin" in c or "northeast" in c
        for c in contents
    )