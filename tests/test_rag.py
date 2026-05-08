from ingestion.loader import load_file
from llm.rag_chain import answer_question, answer_with_history
from llm.session import ChatSession
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

def test_answer_question_returns_correct_keys():
    result = answer_question("What products are in the data?")
    assert "answer"           in result
    assert "sources"          in result
    assert "retrieved_chunks" in result


def test_answer_is_non_empty_string():
    result = answer_question("Which product had highest sales?")
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 0


def test_unanswerable_question():
    result = answer_question("What is the population of Mars?")
    assert "don't have enough data" in result["answer"].lower()


def test_sources_are_returned():
    result = answer_question("Show me pharmacy products")
    assert isinstance(result["sources"], list)
    assert len(result["sources"]) > 0


def test_chat_session_remembers_history():
    session = ChatSession()
    session.ask("Which product had the highest sales?")
    assert len(session.get_history()) == 2


def test_chat_session_clears_history():
    session = ChatSession()
    session.ask("Tell me about pharmacy sales")
    session.clear()
    assert len(session.get_history()) == 0


def test_followup_question_with_history():
    history = [
        {"role": "user",      "content": "Which product had the highest sales?"},
        {"role": "assistant", "content": "Insulin had the highest sales at 91,000."}
    ]
    result = answer_with_history(
        "What region was it in?",
        chat_history=history
    )
    assert "answer" in result
    assert len(result["answer"]) > 0