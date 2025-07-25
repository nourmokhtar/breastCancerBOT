import os
import dotenv
import nest_asyncio
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from together import Together
from langchain_core.runnables import RunnableLambda


# Allow async compatibility
nest_asyncio.apply()
dotenv.load_dotenv()

# === ENV
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# === Embedding
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# === Qdrant Client
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

vectorstore = QdrantVectorStore(
    client=client,
    collection_name="faq_collection",
    embedding=embeddings,
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# === Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful medical chatbot answering based on the following context:\n\n{context}"),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{question}"),
])

# === TogetherChat class
class TogetherChat:
    def __init__(self, prompt, model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"):
        self.prompt = prompt
        self.model = model
        self.client = Together(api_key=TOGETHER_API_KEY)

    def __call__(self, input: dict):
        messages = self.prompt.format_messages(**input)

        # Fix role conversion: map LangChain message type to valid OpenAI/Together roles
        formatted = []
        for m in messages:
            if m.type == "human":
                role = "user"
            elif m.type == "ai":
                role = "assistant"
            elif m.type == "system":
                role = "system"
            else:
                role = "user"  # fallback
            formatted.append({"role": role, "content": m.content})

        # Call Together API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=formatted,
        )

        return response.choices[0].message.content.strip()

llm = RunnableLambda(TogetherChat(prompt=prompt))

# === Utils
def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)

# === Chain
chain = (
    {
        "context": lambda x: format_docs(retriever.invoke(x["question"])),
        "question": lambda x: x["question"],
        "chat_history": lambda x: x["chat_history"],
    }
    | llm
    | StrOutputParser()
)

def get_history(_id):
    return InMemoryChatMessageHistory()

chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history=get_history,
    input_messages_key="question",
    history_messages_key="chat_history"
)

# === CLI Chat Loop
# === Breast Cancer Relevance Filter
def is_breast_cancer_related(text: str) -> bool:
    """Semantic filter: quick keyword check, then zero-shot LLM YES/NO."""
    keywords = ["breast cancer", "mammogram", "tumor", "mastectomy", "her2", "biopsy"]
    if any(k in text.lower() for k in keywords):
        return True

    # Zero-shot check
    system_prompt = (
        "You are an AI classifier. Answer ONLY YES or NO whether this query is about breast cancer or related topics. "
        "The query may be in English or Arabic."
    )
    user_prompt = f"Query: \"{text}\""

    response = llm.invoke({
        "context": "",
        "question": user_prompt,
        "chat_history": []
    })

    return response.strip().lower().startswith("yes")
def is_greeting(text: str) -> bool:
    """Use LLM to detect if the input is a greeting or salutation."""
    system_prompt = (
        "You are an AI classifier. Answer ONLY YES or NO whether the following query is a greeting, salutation, or friendly message. "
        "The query may be in English, Arabic, French, or Tunisian dialect."
    )
    user_prompt = f"Query: \"{text}\""

    response = llm.invoke({
        "context": "",
        "question": user_prompt,
        "chat_history": []
    })

    return response.strip().lower().startswith("yes")

# === CLI Chat Loop
if __name__ == "__main__":
    print("🤖 Breast Cancer Chatbot. Type 'exit' to quit.\n")
    while True:
        q = input("You: ")
        if q.lower() in ["exit", "quit"]:
            break

        if is_greeting(q):
            print("Bot: Hello! 👋 I am your assistant for all things related to breast cancer. How can I help you today?")
            continue

        if not is_breast_cancer_related(q):
            print("Bot: Sorry, I can only answer questions related to breast cancer.")
            continue

        response = chain_with_history.invoke(
            {"question": q},
            config={"configurable": {"session_id": "user-1"}}
        )

        print("Bot:", response)
