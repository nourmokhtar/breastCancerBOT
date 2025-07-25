import os
import glob
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from dotenv import load_dotenv
from qdrant_client.http.models import SearchRequest


# Load environment variables
load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
DOCS_COLLECTION = os.getenv("QDRANT_DOCS_COLLECTION", "docs_collection")
FAQ_COLLECTION = os.getenv("QDRANT_FAQ_COLLECTION", "faq_collection")

# Initialize Qdrant client
qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

def search_faq(query, threshold=0.3, max_hits=1):
    q_emb = embedder.encode([query], convert_to_numpy=True)[0]
    hits = qdrant_client.search(
        collection_name=FAQ_COLLECTION,
        query_vector=q_emb.tolist(),
        limit=max_hits,
        score_threshold=threshold,
        with_payload=True
    )
    if not hits:
        return None
    return hits[0].payload.get("page_content", None)


def search_kb(query, threshold=0.75, max_hits=3):
    q_emb = embedder.encode([query], convert_to_numpy=True)[0]
    hits = qdrant_client.search(
        collection_name=DOCS_COLLECTION,
        query_vector=q_emb.tolist(),
        limit=max_hits,
        score_threshold=threshold,
        with_payload=True
    )
    results = []
    for hit in hits:
        payload = hit.payload
        results.append({
            "source": payload.get("source", "unknown"),
            "chunk": payload.get("chunk", ""),
            "sim": float(hit.score)
        })
    return results

if __name__ == "__main__":
    print("Testing FAQ search...")
    faq_result = search_faq("What are the symptoms of breast cancer?")
    print("FAQ result:", faq_result)

    print("\nTesting KB search...")
    kb_results = search_kb("What are the symptoms of breast cancer?")
    print("KB results:", kb_results)

    print("\nSample FAQ payload:")
    faq_points, _ = qdrant_client.scroll(collection_name=FAQ_COLLECTION, limit=1, with_payload=True)
    print(faq_points[0].payload if faq_points else "No points found.")

    print("\nSample KB payload:")
    kb_points, _ = qdrant_client.scroll(collection_name=DOCS_COLLECTION, limit=1, with_payload=True)
    print(kb_points[0].payload if kb_points else "No points found.")
