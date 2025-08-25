from flask import Flask, request, jsonify, render_template
from query_handler import answer_query, ask_llm_with_context
from speech_io import transcribe_audio_file, text_to_speech, transcribe_live
from translation import detect_language, translate_to_english, translate_from_english
from grammar_correction import correct_grammar
from llm_client import llm
from tensorflow.keras.models import load_model
from keras.preprocessing.image import img_to_array
import cv2
import os
import base64
import numpy as np
import threading
import whisper
from voice_emotion import detect_voice_emotion
from text_to_speech import synthesize_speech
from main import (
    zep_client, get_zep_history, save_zep_message, clear_zep_memory,
    build_history_for_llm, show_recap
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')

face_classifier = cv2.CascadeClassifier('models/Emotion_Detection_CNN/haarcascade_frontalface_default.xml')
model = load_model('models/Emotion_Detection_CNN/model.h5')
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

conversation_history = []

# -------------------------------
# Helper for async TTS
# -------------------------------
def generate_tts_async(reply, lang_code, output_path):
    """Run TTS in background"""
    try:
        synthesize_speech(reply, lang_code=lang_code, output_path=output_path)
        print(f"✅ TTS ready: {output_path}")
    except Exception as e:
        print(f"❌ TTS generation failed: {e}")


@app.route("/zep_test")
def zep_test():
    if not zep_client:
        return jsonify({"status": "fallback", "msg": "⚠️ Zep client not initialized. Using local storage."})

    try:
        save_zep_message("system", "Zep test message")
        hist = get_zep_history()
        return jsonify({
            "status": "ok",
            "msg": "✅ Zep client connected.",
            "history_sample": hist[-3:]
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# -------------------------------
# Query Processing
# -------------------------------
def process_query_with_language(user_input, detected_lang):
    global conversation_history
    
    lang = detected_lang
    if lang and "-" not in lang:
        if lang == "en":
            lang = "en-us"
        elif lang == "fr":
            lang = "fr-fr"
        elif lang == "es":
            lang = "es-es"
        elif lang == "ar":
            lang = "ar-sa"
    
    print(f"🌍 Using provided language: {detected_lang} -> normalized: {lang}")
    
    return _process_query_internal(user_input, lang)


def process_query(user_input):
    global conversation_history

    try:
        lang = detect_language(user_input)
        print(f"🌍 Detected language: {lang}")
    except:
        lang = "en"
    
    if lang and "-" not in lang:
        if lang == "en":
            lang = "en-us"
        elif lang == "fr":
            lang = "fr-fr"
        elif lang == "es":
            lang = "es-es"
        elif lang == "ar":
            lang = "ar-sa"
    
    return _process_query_internal(user_input, lang)


def _process_query_internal(user_input, lang):
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

    save_zep_message("user", user_input_en)

    conversation_history = build_history_for_llm()

    if not any(msg["role"] == "system" for msg in conversation_history):
        system_prompt = {
            "role": "system",
            "content": "You are a kind and helpful assistant for breast cancer patients. "
                       "Answer clearly, supportively, and based on known facts or provided context. "
                       "If you don’t know, say so."
        }
        save_zep_message("system", system_prompt["content"])
        conversation_history.insert(0, system_prompt)

    context_text, source_type = answer_query(user_input_en, return_kb_only=True)

    print(f"\n📤 Retrieved from: {source_type.upper() if source_type else 'UNKNOWN'}")
    print(f"📚 Context:\n{context_text if context_text else '(No context)'}\n")

    if source_type in ["faq", "kb"]:
        try:
            response_en = ask_llm_with_context(user_input_en, context_text)
        except Exception as e:
            print(f"❌ Error in ask_llm_with_context: {e}")
            response_en = "Sorry, I encountered an issue answering that."
    elif source_type == "web":
        response_en = context_text
    else:
        response_en = context_text

    save_zep_message("assistant", response_en)

    try:
        response_local = translate_from_english(response_en, lang)
    except Exception as e:
        print(f"⚠️ Translation from English failed: {e}")
        response_local = response_en

    return response_local, lang


# -------------------------------
# Voice Analysis + TTS
# -------------------------------
@app.route("/analyze_voice", methods=["POST"])
def analyze_voice():
    if "file" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    UPLOAD_FOLDER = "uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    if os.stat(filepath).st_size < 10_000:
        return jsonify({"error": "Audio file too short or empty"}), 400

    try:
        print("🔍 Loading Whisper base model...")
        model = whisper.load_model("base")
        print("🗣️ Transcribing audio...")
        result = model.transcribe(filepath, task="transcribe", language=None)

        transcription = result.get("text", "").strip()
        language = result.get("language", "unknown")

        if not transcription:
            return jsonify({"error": "Whisper failed to transcribe audio"}), 500

        print(f"📜 Transcription: {transcription}")
        print(f"🌐 Detected Language: {language}")

        emotion_result = detect_voice_emotion(filepath)
        emotion_label = emotion_result.get("emotion")
        confidence_str = str(emotion_result.get("confidence", "0")).strip()
        if confidence_str.endswith("%"):
            confidence_str = confidence_str[:-1]
        try:
            confidence_val = float(confidence_str)
        except ValueError:
            confidence_val = 0.0

        if language and language != "unknown":
            reply, lang_local = process_query_with_language(transcription, language)
        else:
            reply, lang_local = process_query(transcription)
        
        print(f"💬 LLM Response: {reply}")

        audio_output_path = os.path.join("static", "llm_response.mp3")
        tts_language = language if language and language != "unknown" else lang_local

        # run TTS in background
        threading.Thread(target=generate_tts_async, args=(reply, tts_language, audio_output_path)).start()

        return jsonify({
            "transcription": transcription,
            "language": language,
            "emotion": emotion_label,
            "confidence": confidence_val,
            "response": reply,
            "audio_url": "/static/llm_response.mp3"
        })

    except Exception as e:
        print(f"❌ Error in voice emotion detection: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------------
# Conversation Utils
# -------------------------------
@app.route("/recap", methods=["GET"])
def recap():
    msgs = get_zep_history()
    if not msgs:
        return jsonify({"recap": "No conversation history."})

    recap_lines = []
    for m in msgs:
        role = (m.get("role") or "").lower()
        content = m.get("content", "")
        who = "You" if role == "user" else "Assistant" if role == "assistant" else "System"
        recap_lines.append(f"{who}: {content}")

    return jsonify({"recap": "\n".join(recap_lines)})


@app.route("/clear_history", methods=["POST"])
def clear_history():
    success = clear_zep_memory()
    return jsonify({"cleared": success})


# -------------------------------
# Text Query + TTS
# -------------------------------
@app.route("/api/query", methods=["POST"])
def handle_query():
    data = request.json
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Empty input"}), 400

    reply, lang = process_query(user_input)

    audio_output_path = os.path.join("static", "llm_response.mp3")
    threading.Thread(target=generate_tts_async, args=(reply, lang, audio_output_path)).start()

    return jsonify({
        "response": reply,
        "language": lang,
        "audio_url": "/static/llm_response.mp3"
    })


@app.route("/chat")
def chat_interface():
    return render_template("index.html")


@app.route('/analyze_frame', methods=['POST'])
def analyze_frame():
    return jsonify({"error": "Frame analysis is disabled (models commented out)"}), 501


# -------------------------------
# Run App
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
