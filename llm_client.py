from together import Together
from config import TOGETHER_API_KEY
class TogetherChat:
    def __init__(self, model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"):
        self.client = Together(api_key=TOGETHER_API_KEY)
        self.model = model

    def __call__(self, messages):
        # messages are list of dicts with 'role' and 'content' keys
        formatted = [{"role": m["role"], "content": m["content"]} for m in messages]
        resp = self.client.chat.completions.create(model=self.model, messages=formatted, stream=False)
        return resp.choices[0].message.content.strip()
llm = TogetherChat()