
import os
import glob
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from dotenv import load_dotenv
from qdrant_client.http.models import SearchRequest
from qdrant_client import QdrantClient

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
hits, _ = qdrant_client.scroll(
    collection_name=DOCS_COLLECTION,
    with_payload=True,
    limit=5
)

for hit in hits:
    print(json.dumps(hit.payload, indent=2, ensure_ascii=False))