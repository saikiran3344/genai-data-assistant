from llm.rag_chain import answer_with_history

class ChatSession:
    """
    Manages a single user's conversation history.
    Each session is independent — multiple users get separate sessions.
    """
    def __init__(self, max_history: int =10):
        self.history = []
        self.max_history = max_history

    def ask(self, question: str) -> dict:
        result = answer_with_history(
            question = question, chat_history= self.history
        )

        self.history.append({
            "role": "user",
            "content": question
        })
        self.history.append({
            "role": "assistant",
            "content": result["answer"]
        })

        if len(self.history) >self.max_history * 2:
            self.history = self.history[-(self.max_history * 2):]
        
        return result
    
    def clear(self):
        self.history= []
        print("Conversation history cleared")
    
    def get_history(self) -> list[dict]:
        return self.history

if __name__ == "__main__":
    session = ChatSession()

    questions = [
        "What products do we have in the data?",
        "Which one had the highest sales in pharmacy products?",
        "What region was it in?",
        "What about OTC products, which had the best sales?",
        "What is the total sales across all products?"
    ]

    print("Starting conversation session...\n")
    for q in questions:
        print(f"You: {q}")
        result = session.ask(q)
        print(f"Assistant: {result['answer']}")
        print(f"(Used {result['retrieved_chunks']} chunks)\n")