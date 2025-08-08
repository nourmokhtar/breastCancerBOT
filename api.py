from flask import Flask, request, jsonify, render_template
from query_handler import answer_query
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
from voice_emotion import detect_voice_emotion
from text_to_speech import synthesize_speech
import whisper



app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')
face_classifier = cv2.CascadeClassifier('models/Emotion_Detection_CNN/haarcascade_frontalface_default.xml')
model = load_model('models/Emotion_Detection_CNN/model.h5')
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

conversation_history = []
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

def process_query_with_language(user_input, detected_lang):
    """Process query using a pre-detected language (e.g., from Whisper)"""
    global conversation_history
    
    # Use the provided language and normalize it
    lang = detected_lang
    
    # Normalize language code to ensure consistency
    if lang and "-" not in lang:
        # Add region code for better accent matching
        if lang == "en":
            lang = "en-us"  # Default to US English for text input
        elif lang == "fr":
            lang = "fr-fr"  # Default to French French
        elif lang == "es":
            lang = "es-es"  # Default to Spanish Spanish
        elif lang == "ar":
            lang = "ar-sa"  # Default to Saudi Arabic
    
    print(f"🌍 Using provided language: {detected_lang} -> normalized: {lang}")
    
    return _process_query_internal(user_input, lang)

def process_query(user_input):
    global conversation_history

    try:
        lang = detect_language(user_input)
        print(f"🌍 Detected language: {lang}")
    except:
        lang = "en"
    
    # Normalize language code to ensure consistency
    if lang and "-" not in lang:
        # Add region code for better accent matching
        if lang == "en":
            lang = "en-us"  # Default to US English for text input
        elif lang == "fr":
            lang = "fr-fr"  # Default to French French
        elif lang == "es":
            lang = "es-es"  # Default to Spanish Spanish
        elif lang == "ar":
            lang = "ar-sa"  # Default to Saudi Arabic
    
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

@app.route("/analyze_voice", methods=["POST"])
def analyze_voice():
    if "file" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    UPLOAD_FOLDER = "uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Assure que le dossier existe

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Check file size
    if os.stat(filepath).st_size < 10_000:
        return jsonify({"error": "Audio file too short or empty"}), 400

    try:
        print("🔍 Loading Whisper base model...")
        model = whisper.load_model("base")  # or "tiny" for speed

        print("🗣️ Transcribing audio...")
        result = model.transcribe(filepath, task="transcribe", language=None)

        transcription = result.get("text", "").strip()
        language = result.get("language", "unknown")

        if not transcription:
            return jsonify({"error": "Whisper failed to transcribe audio"}), 500

        print(f"📜 Transcription: {transcription}")
        print(f"🌐 Detected Language: {language}")

        # 🎭 Emotion Detection
        emotion_result = detect_voice_emotion(filepath)
        emotion_label = emotion_result.get("emotion")
        confidence_str = str(emotion_result.get("confidence", "0")).strip()
        # Normalize confidence to a numeric value (no percent sign)
        if confidence_str.endswith("%"):
            confidence_str = confidence_str[:-1]
        try:
            confidence_val = float(confidence_str)
        except ValueError:
            confidence_val = 0.0

        # 🤖 Full RAG pipeline with Whisper language detection
        # Use Whisper's language detection instead of langdetect for voice input
        if language and language != "unknown":
            # Use Whisper's detected language for processing
            reply, lang_local = process_query_with_language(transcription, language)
        else:
            # Fallback to normal language detection
            reply, lang_local = process_query(transcription)
        
        print(f"💬 LLM Response: {reply}")

        # 🔊 Text-to-Speech (gTTS outputs mp3)
        # Use Whisper-detected language for better accent matching
        audio_output_path = os.path.join("static", "llm_response.mp3")
        print(f"[Whisper] Detected language: {language} | RAG language: {lang_local}")
        # Use Whisper language for TTS to get better accent matching
        tts_language = language if language and language != "unknown" else lang_local
        synthesize_speech(reply, lang_code=tts_language, output_path=audio_output_path)
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
    
@app.route("/api/query", methods=["POST"])
def handle_query():
    data = request.json
    user_input = data.get("message", "").strip()

    if not user_input:
        return jsonify({"error": "Empty input"}), 400

    reply, lang = process_query(user_input)

    # Synthesize TTS for text-submitted queries as well
    audio_output_path = os.path.join("static", "llm_response.mp3")
    try:
        # Use the normalized language code for better accent matching
        synthesize_speech(reply, lang_code=lang, output_path=audio_output_path)
        audio_url = "/static/llm_response.mp3"
    except Exception as e:
        print(f"[TTS] Error in text query: {e}")
        audio_url = None

    return jsonify({
        "response": reply,
        "language": lang,
        "audio_url": audio_url
    })


@app.route("/chat")
def chat_interface():
    return render_template("index.html")

@app.route('/analyze_frame', methods=['POST'])
def analyze_frame():
    data = request.get_json()
    image_data = data.get("image", "")
    
    if not image_data:
        return jsonify({"error": "No image data provided"}), 400

    try:
        image_data = image_data.split(",")[1]  # Remove base64 header
        image_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # Detect faces
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_classifier.detectMultiScale(gray, 1.3, 5)

        if len(faces) == 0:
            print("⚠️ No face detected in frame.")
            return jsonify({"results": []})

        for (x, y, w, h) in faces:
            roi = gray[y:y+h, x:x+w]
            roi = cv2.resize(roi, (48, 48))
            roi = roi.astype("float") / 255.0
            roi = img_to_array(roi)
            roi = np.expand_dims(roi, axis=0)

            prediction = model.predict(roi)[0]
            emotion_index = np.argmax(prediction)
            emotion_label = emotion_labels[emotion_index]
            confidence = float(np.max(prediction)) * 100

            print(f"🎯 Emotion Detected: {emotion_label} ({confidence:.2f}%)")

            return jsonify({
                "results": [
                    {
                        "label": emotion_label,
                        "confidence": f"{confidence:.2f}"
                    }
                ]
            })

    except Exception as e:
        print(f"❌ Error analyzing frame: {e}")
        return jsonify({"error": "Failed to process image"}), 500
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
