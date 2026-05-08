import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
#from langchain.schema import HumanMessage, AIMessage
from vectorstore.store import similarity_search
from llm.prompts import RAG_PROMPT, CHAT_PROMPT

load_dotenv()

def get_llm():
    return ChatOllama(
        model=os.getenv("OLLAMA_LLM_MODEL", "llama3.2"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature = 0,
        num_predict = 512,
    )

def format_context(documents) -> str:
    """
    Combine retrieved chunks into a single context string.
    Each chunk is numbered so the LLM can reference them clearly.
    """
    if not documents:
        return "No relevant data is found."
    
    context_parts = []
    for i, doc in enumerate(documents, 1):
        context_parts.append(f"[{i}] {doc.page_content}")
    total = len(context_parts)
    header = f"Total records retrieved: {total}\n"

    return header + "\n".join(context_parts)

def format_chat_history(history: list[dict]) -> str:
    """
    Convert chat history list into a readable string for the prompt.
    """
    if not history:
        return "No previous conversation."
    
    lines = []
    for turn in history:
        role = "User" if turn["role"] == "user" else "Assistant"
        lines.append(f"{role}: {turn['content']}")
    return "\n".join(lines)

def answer_question(question: str, k: int = 10) -> dict:
    """
    Single-turn Q&A — no memory of previous questions.
    Use this for one-off queries.
    """
    print(f"\n Searching for relevant context....")
    docs =similarity_search(question, k=k)

    if not docs:
        return {
            "answer": "I don't have enough data to answer this question.",
            "sources": [],
            "retrieved_chunks": 0
        }
    context = format_context(docs)
    prompt = RAG_PROMPT.format(context = context, question=question)

    print(f"Retrieved {len(docs)} chunks. Generating answer....")
    llm = get_llm()
    response = llm.invoke(prompt)

    sources = []

    for doc in docs:
        source_info = {
            "source": doc.metadata.get("source", "unknown"),
            "type": doc.metadata.get("type", "unknown"),
            "score": doc.metadata.get("similarity_score",0.0)
        }

        if doc.metadata.get("page") is not None:
            source_info["page"] = doc.metadata["page"]
        if doc.metadata.get("row") is not None:
            source_info["row"] = doc.metadata["row"]

        if source_info not in sources:
            sources.append(source_info)
    return {
        "answer": response.content,
        "sources": sources,
        "retrieved_chunks": len(docs)
    }

def answer_with_history(
        question: str, chat_history: list[dict], k: int = 10) -> dict:
    """
    Multi-turn Q&A — uses conversation history for follow-up questions.
    chat_history format: [{"role": "user/assistant", "content": "..."}]
    """
    print(f"\n Searching for relevant context....")
    if chat_history:
        enhanced_query = f"{question} {chat_history[-1]['content']}"
    else:
        enhanced_query = question
    docs = similarity_search(enhanced_query, k=k)

    if not docs:
        return {
            "answer": "I don't have enough data to answer this question.",
            "sources": [],
            "retrieved_chunks": 0
        }
    context = format_context(docs)
    history_text = format_chat_history(chat_history)

    prompt = CHAT_PROMPT.format(
        context = context, chat_history = history_text, question = question
    )

    print(f"\n Retrieved {len(docs)} chunks. Generating answer....")
    llm = get_llm()
    response = llm.invoke(prompt)

    sources = []

    for doc in docs:
        source_info = {
            "source": doc.metadata.get("source", "unknown"),
            "type": doc.metadata.get("type", "unknown"),
            "score": doc.metadata.get("similarity_score",0.0)
        }

        if source_info not in sources:
            sources.append(source_info)
    
    return {
        "answer": response.content,
        "sources": sources,
        "retrieved_chunks": len(docs)
    }

# Test by running directly
if __name__ == "__main__":
    print("=" * 50)
    print("Test 1 — Single question")
    print("=" * 50)
    result = answer_question("Which product had the highest sales?")
    print(f"Answer: {result['answer']}")
    print(f"Sources: {result['sources']}")
    print(f"Chunks used: {result['retrieved_chunks']}")

    print()
    print("=" * 50)
    print("Test 2 — Follow-up question with history")
    print("=" * 50)
    history = [
        {"role": "user",      "content": "Which product had the highest sales?"},
        {"role": "assistant", "content": "Aspirin had the highest sales at 78,000 in the west region during Q2."}
    ]
    result2 = answer_with_history(
        "What region was it in?",
        chat_history=history
    )
    print(f"Answer: {result2['answer']}")
    print(f"Chunks used: {result2['retrieved_chunks']}")

    print()
    print("=" * 50)
    print("Test 3 — Question with no answer in data")
    print("=" * 50)
    result3 = answer_question("What is the weather in Austin today?")
    print(f"Answer: {result3['answer']}")