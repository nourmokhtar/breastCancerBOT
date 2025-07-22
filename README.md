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
