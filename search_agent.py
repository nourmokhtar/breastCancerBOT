import requests
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from config import SERPER_API_KEY
import os
import numpy as np
from embedding_search import embedder
import uuid
from qdrant_client import QdrantClient


QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
DOCS_COLLECTION = os.getenv("QDRANT_DOCS_COLLECTION", "docs_collection")

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)
def search_serper(query):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json={"q": query})
        response.raise_for_status()
        results = response.json().get('organic', [])
        return [item['link'] for item in results]
    except Exception as e:
        print("Search error:", e)
        return []

async def fetch_text(url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            html = await page.content()
            await browser.close()
        return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"Scraping error ({url}): {e}")
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser").get_text(separator="\n", strip=True)
        except Exception as e2:
            print(f"Fallback failed ({url}): {e2}")
            return ""
        
def register_search_in_kb(query, answer, source="search_agent_fallback"):
    vector = embedder.encode([answer], convert_to_numpy=True)[0]
    payload = {
        "chunk": answer,
        "source": source,
        "original_query": query
    }
    qdrant_client.upsert(
        collection_name=DOCS_COLLECTION,
        points=[
            {
                "id": str(uuid.uuid4()),  # ✅ Unique ID
                "vector": vector.tolist(),
                "payload": payload
            }
        ]
    )
    

async def search_agent_fallback(query, max_links=3):
    links = search_serper(query)
    if not links:
        return "Sorry, no online info found."

    from llm_client import llm  # import here to avoid circular

    for link in links[:max_links]:
        content = await fetch_text(link)
        if not content:
            continue
        messages = [
            {"type": "system", "content": "You are compassionate assistant knowledgeable about breast cancer and mental health support. respond with clear answers that arent too long "},
            {"type": "user", "content": f"Question: {query}\n\nContent:\n{content[:15000]}"}
        ]
        answer = llm(messages)
        if answer.strip():
            return f"\n{answer}"
    return "Sorry, couldn't extract a good answer from the web."
