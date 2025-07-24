import os
import glob
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

def load_faq(path="faq.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = [item["question"] for item in data]
    answers = [item["answer"] for item in data]
    return questions, answers

faq_questions, faq_answers = load_faq()
faq_vectors = embedder.encode(faq_questions, convert_to_numpy=True)
faq_index = faiss.IndexFlatL2(faq_vectors.shape[1])
faq_index.add(faq_vectors)

def load_kb(folder="kb"):
    chunks, sources = [], []
    for md_file in glob.glob(os.path.join(folder, "*.md")):
        text = open(md_file, "r", encoding="utf-8").read()
        parts = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
        chunks.extend(parts)
        sources.extend([os.path.basename(md_file)] * len(parts))
    return chunks, sources

kb_chunks, kb_sources = load_kb()
kb_vectors = embedder.encode(kb_chunks, convert_to_numpy=True)
kb_vectors_norm = kb_vectors / np.linalg.norm(kb_vectors, axis=1, keepdims=True)

def search_faq(query, threshold=0.3):
    vec = embedder.encode([query], convert_to_numpy=True)
    D, I = faq_index.search(vec, k=1)
    if D[0][0] < threshold:
        return faq_answers[I[0][0]]
    return None

def search_kb(query, threshold=0.75, max_hits=3):
    q_emb = embedder.encode([query], convert_to_numpy=True)
    q_emb_norm = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)
    sims = kb_vectors_norm.dot(q_emb_norm.T).squeeze()
    idxs = np.where(sims >= threshold)[0]
    if len(idxs) == 0:
        return []
    sorted_idxs = idxs[np.argsort(-sims[idxs])]
    return [{"source": kb_sources[i], "chunk": kb_chunks[i], "sim": float(sims[i])} for i in sorted_idxs[:max_hits]]
