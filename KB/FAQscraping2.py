import requests
from bs4 import BeautifulSoup
import json
import os

# Step 1: Scrape the site
url = "https://breast-cancer.adelphi.edu/education/breast-cancer-information/frequently-asked-questions/"
headers = {
    "User-Agent": "Mozilla/5.0"
}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, "html.parser")

faq_blocks = soup.select("div.expandable")

new_faqs = []

for block in faq_blocks:
    label = block.find("label")
    question = label.get_text(strip=True) if label else None
    answer_div = label.find_next_sibling("div") if label else None
    if answer_div:
        answer = answer_div.get_text(separator=" ", strip=True)
        new_faqs.append({
            "question": question,
            "answer": answer,
            "source": url
        })

# Step 2: Load existing data from FAQ.json
faq_file = "FAQ.json"

if os.path.exists(faq_file):
    with open(faq_file, "r", encoding="utf-8") as f:
        try:
            existing_faqs = json.load(f)
        except json.JSONDecodeError:
            existing_faqs = []
else:
    existing_faqs = []

# Step 3: Append new FAQs
existing_faqs.extend(new_faqs)

# Step 4: Save back to file
with open(faq_file, "w", encoding="utf-8") as f:
    json.dump(existing_faqs, f, indent=2, ensure_ascii=False)

print(f"✅ Appended {len(new_faqs)} FAQs with source to {faq_file}")
