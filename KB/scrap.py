import json
import requests
from bs4 import BeautifulSoup

url = "https://www.randolphhealth.org/services/breast-center/breast-health-frequently-asked-questions/"
source = url

def scrape_faq():
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    content = soup.find("div", class_="componentContent")
    if not content:
        print("❌ Could not find FAQ section.")
        return []

    divs = content.find_all("div")

    faqs = []
    current_question = None
    current_answer = ""

    for div in divs:
        text = div.get_text(strip=True)

        # Identify a new question
        if text.endswith("?") and len(text) < 200:
            if current_question and current_answer:
                faqs.append({
                    "question": current_question,
                    "answer": current_answer.strip(),
                    "source": source
                })
            current_question = text
            current_answer = ""
        else:
            current_answer += " " + text

    # Add the last question
    if current_question and current_answer:
        faqs.append({
            "question": current_question,
            "answer": current_answer.strip(),
            "source": source
        })

    return faqs

def main():
    faqs = scrape_faq()
    with open("FAQ.json", "w", encoding="utf-8") as f:
        json.dump(faqs, f, indent=2, ensure_ascii=False)
    print(f"✅ Done! Extracted {len(faqs)} FAQs to FAQ.json")

if __name__ == "__main__":
    main()
