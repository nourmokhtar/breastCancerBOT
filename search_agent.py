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
    try:
        vector = embedder.encode([answer], convert_to_numpy=True)[0]
        print(f"Registering search result in KB... (source={source})")
        print(f"Vector shape: {vector.shape}")

        payload = {
            "chunk": answer,
            "source": source,
            "original_query": query
        }

        qdrant_client.upsert(
            collection_name=DOCS_COLLECTION,
            points=[
                {
                    "id": str(uuid.uuid4()),
                    "vector": vector.tolist(),
                    "payload": payload
                }
            ]
        )
        print("✅ Upserted into Qdrant successfully.")

    except Exception as e:
        print(f"❌ Failed to upsert into Qdrant: {e}")

async def search_agent_fallback(query: str) -> str:
    system_prompt = "You are a helpful assistant specializing in breast cancer information. Answer using known medical facts. If unsure, say so."
    user_message = f"The user asked: {query}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    try:
        response = llm(messages)
        return response
    except Exception as e:
        print(f"❌ Fallback LLM failed: {e}")
        return "I couldn’t find a reliable answer at the moment. Please consult a medical professional."
