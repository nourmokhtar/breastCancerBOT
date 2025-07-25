import os
import json
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, CollectionStatus
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables from .env
load_dotenv()

# ENV variables
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")  # If needed for LLM later

# Paths
FAQ_PATH = "KB/FAQ/FAQ.json"
DOCS_PATH = "KB/breast_cancer_general_kb"

# Embedding model (OpenAI-compatible)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Qdrant Cloud client
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

def recreate_collection_if_exists(name):
    try:
        info = client.get_collection(name)
        if info.status == CollectionStatus.GREEN:
            client.delete_collection(name)
            print(f"Deleted existing collection '{name}'")
    except Exception:
        pass  # Collection doesn't exist

    client.recreate_collection(
        collection_name=name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    print(f"Created new collection '{name}'")

def load_faq_documents():
    documents = []
    with open(FAQ_PATH, 'r', encoding='utf-8') as f:
        faqs = json.load(f)
        for faq in faqs:
            content = f"Q: {faq['question']}\nA: {faq['answer']}"
            metadata = {"source": faq.get("source", ""), "type": "faq"}
            documents.append(Document(page_content=content, metadata=metadata))
    return documents

def load_text_documents():
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    documents = []

    for root, _, files in os.walk(DOCS_PATH):
        for file in files:
            if file.lower().endswith((".txt", ".md")):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                    splits = text_splitter.split_text(raw_text)
                    for chunk in splits:
                        documents.append(Document(page_content=chunk, metadata={"source": path, "type": "doc"}))
    return documents

def build_vector_store():
    # Recreate collections
    recreate_collection_if_exists("faq_collection")
    recreate_collection_if_exists("docs_collection")

    # Load and index FAQ
    faq_docs = load_faq_documents()
    Qdrant.from_documents(
        faq_docs,
        embedding=embeddings,
        collection_name="faq_collection",
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY
    )
    print(f"Indexed {len(faq_docs)} FAQs")

    # Load and index documents
    doc_docs = load_text_documents()
    Qdrant.from_documents(
        doc_docs,
        embedding=embeddings,
        collection_name="docs_collection",
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY
    )
    print(f"Indexed {len(doc_docs)} general KB documents")

if __name__ == "__main__":
    build_vector_store()
