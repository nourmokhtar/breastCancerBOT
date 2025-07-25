import requests
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

SERPER_API_KEY = "bf22d413e5e07dfbd9d20c33df2dba8c2b0dfa50"

def search_serper(query):
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json={"q": query})
        response.raise_for_status()
        results = response.json().get('organic', [])
        return [item['link'] for item in results]
    except Exception as e:
        print(f"[Search Error] {e}")
        return []

async def fetch_text(url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            html = await page.content()
            await browser.close()
            text = BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
            return text
    except Exception as e:
        print(f"[Scraping error {url}]: {e}")
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser").get_text(separator="\n", strip=True)
        except Exception as e2:
            print(f"[Fallback failed {url}]: {e2}")
            return ""

async def search_agent_fallback(llm, query, max_links=3):
    links = search_serper(query)
    if not links:
        return "Sorry, no online info found."

    for link in links[:max_links]:
        content = await fetch_text(link)
        if not content:
            continue

        messages = [
            {"type": "system", "content": "You are a compassionate assistant knowledgeable about breast cancer and mental health support."},
            {"type": "user", "content": f"Question: {query}\n\nContent:\n{content[:15000]}"}
        ]

        answer = llm(messages)

        if answer.strip():
            return answer

    return "Sorry, couldn't extract a good answer from the web."

# Dummy LLM function for testing - just echoes back the user question and first 100 chars of content
def dummy_llm(messages):
    user_msg = next(m["content"] for m in messages if m["type"] == "user")
    return f"Dummy LLM response based on query:\n{user_msg[:200]}"

if __name__ == "__main__":
    query = "Can I get a mammogram that doesn't compress my breast?"

    result = asyncio.run(search_agent_fallback(dummy_llm, query))
    print("\nSearch Agent Result:\n", result)
