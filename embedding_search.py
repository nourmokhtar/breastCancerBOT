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

def search_faq(query, threshold=0.7, max_hits=1):
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


def search_kb(query, top_k=3):
    query_vector = embedder.encode([query], convert_to_numpy=True)[0]
    results = []

    try:
        hits = qdrant_client.search(
            
            collection_name=DOCS_COLLECTION,
            query_vector=query_vector.tolist(),
            limit=top_k,
            with_payload=True
        )

        for hit in hits:
            payload = hit.payload
            # Try chunk first (fallback data)
            content = payload.get("chunk")
            if not content:
                # Then try page_content (old KB)
                content = payload.get("page_content", "")

            metadata = payload.get("metadata", {})
            source = metadata.get("source") or payload.get("source", "unknown")
            sim = hit.score

            if sim > 0.75 and content.strip():
                results.append({
                    "chunk": content,
                    "sim": sim,
                    "source": source
                })

        return results

    except Exception as e:
        print(f"❌ Qdrant search failed: {e}")
        return []
