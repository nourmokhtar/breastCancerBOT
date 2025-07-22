# Chatbot Project

## Setup Instructions

### 1. Clone the repository (if you haven’t already):
```bash
git clone <your-repo-url>
cd chatbot
```
### 2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate
```
On macOS/Linux, activate with:
```bash
source venv/bin/activate
```
###3. Install dependencies:
```bash
pip install -r requirements.txt
```
###4. Set up environment variables:
Create a .env file in the project root with your API keys and Qdrant URL. Example:
```.env
TOGETHER_API_KEY=your_together_api_key
QDRANT_URL=https://your-qdrant-url
QDRANT_API_KEY=your_qdrant_api_key
```
###5. Index your knowledge base (run once, or when KB changes):
```bash
python vectorStore.py
```
###6. Start the chatbot:
```bash
python chat.py
```
## Breast Cancer Chatbot – RAG-based AI Agent --- DESCRIPTION

This project is an intelligent chatbot designed to assist users by answering questions related to **breast cancer**. It leverages a **Retrieval-Augmented Generation (RAG)** approach and integrates with **Qdrant**, a vector database for efficient semantic search.

### 🔍 How It Works

1. **Initial Filtering:**  
   The chatbot first analyzes user input to determine if the question is related to breast cancer.

2. **FAQ Lookup:**  
   If the question is relevant, the agent first tries to answer using pre-curated **Frequently Asked Questions** (FAQ).

3. **General Knowledge Retrieval:**  
   If no answer is found in the FAQ, it searches through broader **domain documents** related to breast cancer.

4. **Fallback to Search Agent:**  
   If nothing is found in the above steps, the system activates a more advanced **search agent** to provide the best possible response.

5. **Answer Storage:**  
   Every valid interaction is logged and stored into the **Knowledge Base (KB)** to continuously improve future responses.

---

