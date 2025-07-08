from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

url = "https://www.randolphhealth.org/services/breast-center/breast-health-frequently-asked-questions/"
source = url

def scrape_with_selenium():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    time.sleep(3)  # wait for page to load fully

    faqs = []

    try:
        # Find all questions (h3 tags inside the accordion div with id breastFAQ)
        questions = driver.find_elements(By.CSS_SELECTOR, "#breastFAQ > h3")

        for question in questions:
            question_text = question.text.strip()

            # The answer is the next sibling <div> after the <h3>
            answer_div = question.find_element(By.XPATH, "following-sibling::div[1]")
            answer_text = answer_div.text.strip()

            if question_text and answer_text:
                faqs.append({
                    "question": question_text,
                    "answer": answer_text,
                    "source": source
                })

    except Exception as e:
        print(f"Error while scraping: {e}")

    driver.quit()
    return faqs

def main():
    faqs = scrape_with_selenium()
    with open("FAQ.json", "w", encoding="utf-8") as f:
        json.dump(faqs, f, indent=2, ensure_ascii=False)
    print(f"✅ Done! Extracted {len(faqs)} FAQs to FAQ.json")

if __name__ == "__main__":
    main()
