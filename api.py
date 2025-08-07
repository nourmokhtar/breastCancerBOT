from flask import Flask, request, jsonify, render_template
from query_handler import answer_query
from speech_io import transcribe_audio_file, text_to_speech, transcribe_live
from translation import detect_language, translate_to_english, translate_from_english
from grammar_correction import correct_grammar
from llm_client import llm

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')

conversation_history = []

def process_query(user_input):
    global conversation_history

    try:
        lang = detect_language(user_input)
        print(f"🌍 Detected language: {lang}")
    except:
        lang = "en"

    try:
        if lang in ["en", "fr", "ar"]:
            user_input = correct_grammar(user_input, lang)
            print(f"✍️ Corrected input: {user_input}")
    except Exception as e:
        print(f"⚠️ Grammar correction failed: {e}")

    try:
        user_input_en = translate_to_english(user_input, lang)
    except Exception as e:
        print(f"⚠️ Translation to English failed: {e}")
        user_input_en = user_input

    conversation_history.append({"role": "user", "content": user_input_en})

    if not any(msg["role"] == "system" for msg in conversation_history):
        conversation_history.insert(0, {
            "role": "system",
            "content": "You are a kind and helpful assistant for breast cancer patients. Answer clearly, supportively, and based on known facts or provided context. If you don’t know, say so."
        })

    # 🔍 Context
    context_text, source_type = answer_query(user_input_en, return_kb_only=True)

    print(f"\n📤 Retrieved from: {source_type.upper() if source_type else 'UNKNOWN'}")
    print(f"📚 Context:\n{context_text if context_text else '(No context)'}\n")

    if context_text and source_type not in ["greeting", "not_relevant"]:
        conversation_history.append({
            "role": "system",
            "content": f"Relevant knowledge ({source_type}):\n{context_text}"
        })

    try:
        response_en = llm(conversation_history)
    except Exception as e:
        print(f"❌ LLM error: {e}")
        response_en = "Sorry, I encountered an issue answering that."

    conversation_history.append({"role": "assistant", "content": response_en})

    try:
        response_local = translate_from_english(response_en, lang)
    except Exception as e:
        print(f"⚠️ Translation from English failed: {e}")
        response_local = response_en

    return response_local, lang


@app.route("/api/query", methods=["POST"])
def handle_query():
    data = request.json
    user_input = data.get("message", "").strip()

    if not user_input:
        return jsonify({"error": "Empty input"}), 400

    reply, lang = process_query(user_input)
    return jsonify({
        "response": reply,
        "language": lang
    })


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/chat")
def chat_interface():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
