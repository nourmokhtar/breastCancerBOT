import requests
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from config import SERPER_API_KEY

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
            {"type": "system", "content": "You are compassionate assistant knowledgeable about breast cancer and mental health support."},
            {"type": "user", "content": f"Question: {query}\n\nContent:\n{content[:15000]}"}
        ]
        answer = llm(messages)
        if answer.strip():
            return f"\n{answer}"
    return "Sorry, couldn't extract a good answer from the web."

if __name__ == "__main__":
    import asyncio

    query = "What are the symptoms of breast cancer?"
    result = asyncio.run(search_agent_fallback(query))
    print("Search Agent Result:\n", result)
