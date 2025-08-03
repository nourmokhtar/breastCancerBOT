# query_handler.py
from translation import detect_language, translate_to_english, translate_from_english
from embedding_search import search_faq, search_kb
from llm_client import llm
import asyncio
from search_agent import search_agent_fallback,register_search_in_kb
from qdrant_client import QdrantClient
import os
import numpy as np
from embedding_search import embedder
import uuid

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
DOCS_COLLECTION = os.getenv("QDRANT_DOCS_COLLECTION", "docs_collection")

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

def detect_greeting_language(query: str) -> str:
    """
    Heuristic-based greeting language detection for common greetings.
    """
    q = query.lower()
    if any(w in q for w in ["عسلامة", "مرحبا", "السلام عليكم", "أهلا", "أهلاً", "أهلا وسهلا"]):
        return "ar"
    if any(w in q for w in ["bonjour", "salut"]):
        return "fr"
    if any(w in q for w in ["hi", "hello", "hey"]):
        return "en"
    return None

def is_breast_cancer_related(text: str) -> bool:
    """
    Quick keyword-based check, then use LLM classification to confirm
    if the query is about breast cancer or related topics.
    """
    keywords = ["breast cancer", "mammogram", "tumor", "mastectomy", "her2", "biopsy"]
    if any(k in text.lower() for k in keywords):
        return True

    system_prompt = (
        "You are an AI classifier. Answer ONLY YES or NO whether this query is about breast cancer or related topics. "
        "The query may be in English, Arabic, or French."
    )
    user_prompt = f"Query: \"{text}\""
    
    resp = llm([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    
    return resp.strip().lower().startswith("yes")


def ask_llm_with_context(question: str, context: str, lang: str = "en") -> str:
    """
    Use LLM to answer a question based strictly on given context.
    Includes empathetic support for breast cancer patients.
    """
    lang_map = {"en": "English", "ar": "Arabic", "fr": "French"}
    lang_name = lang_map.get(lang, "English")
    prompt = f"""
You are a helpful, empathetic medical assistant AI for breast cancer patients.
Use ONLY the CONTEXT below to answer the question.
Answer in {lang_name}. Include a supportive message or mental health tip when appropriate in Tunisia.
If the answer is not contained, say 'I don't have the answer.'

QUESTION: {question}

CONTEXT:
{context}
"""
    
    # THIS is where you call the llm
    return llm([{"role": "system", "content": prompt}])
def answer_query(query: str, return_kb_only=False):
    """
    Answer query using a clear three-step fallback: FAQ → KB → Web.
    Only one is used per query (no mixing).
    If return_kb_only=True, returns (context, source_type)
    """
    # Step 1: Greeting
    greeting_words = {"hi", "hello", "hey", "salut", "bonjour", "مرحبا", "السلام عليكم", "أهلا", "أهلاً", "أهلا وسهلا", "عسلامة"}
    greetings_map = {
        "ar": "👋 مرحبًا! أنا هنا لتقديم معلومات ودعم حول سرطان الثدي. اسألني ما تشاء.",
        "fr": "👋 Bonjour ! Je suis là pour vous informer et vous soutenir sur le cancer du sein. Posez-moi vos questions.",
        "en": "👋 Hello! I'm here for breast cancer info & support. Ask me anything."
    }

    query_lower = query.lower()
    if any(word in query_lower for word in greeting_words):
        lang = detect_greeting_language(query) or detect_language(query)
        greeting = greetings_map.get(lang, greetings_map["en"])
        return (greeting, "greeting") if return_kb_only else greeting

    # Step 2: Translate to English
    lang = detect_language(query)
    query_en = translate_to_english(query, lang)

    # Step 3: Breast cancer relevance check
    if not is_breast_cancer_related(query_en):
        reason = {
            "ar": "❌ أستطيع فقط الإجابة على الأسئلة المتعلقة بسرطان الثدي.",
            "fr": "❌ Je ne peux répondre qu'aux questions sur le cancer du sein.",
        }.get(lang, "❌ I can only answer questions about breast cancer.")
        return (reason, "not_relevant") if return_kb_only else reason

    # Step 4: Try FAQ
    faq_answer = search_faq(query_en)
    if faq_answer:
        if return_kb_only:
            return (faq_answer, "faq")
        translated = faq_answer if lang == "en" else translate_from_english(faq_answer, lang)
        return f"✅ FAQ: {translated}\n\n{('اسأل المزيد إذا أردت!' if lang == 'ar' else 'N’hésitez pas à poser plus de questions !' if lang == 'fr' else 'Ask more if you like!')}"

    # Step 5: Try KB
    kb_hits = search_kb(query_en)
    if kb_hits:
        context = "\n\n---\n\n".join(f"[{h['source']} | sim={h['sim']:.3f}]\n{h['chunk']}" for h in kb_hits)
        if return_kb_only:
            return (context, "kb")
        kb_response_en = ask_llm_with_context(query_en, context)
        final = translate_from_english(kb_response_en, lang) if lang != "en" else kb_response_en
        return f"📚 KB: {final}"

    # Step 6: Web Search (last resort)
    web_fallback_en = asyncio.run(search_agent_fallback(query_en))
    if return_kb_only:
        return (web_fallback_en, "web")
    final = translate_from_english(web_fallback_en, lang) if lang != "en" else web_fallback_en
    register_search_in_kb(query_en, web_fallback_en, source="search_agent_fallback")
    return f"🌐 Web: {final}"
