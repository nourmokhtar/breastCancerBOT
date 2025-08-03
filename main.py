# main.py
import sys
from query_handler import answer_query
from speech_io import transcribe_audio_file, text_to_speech, transcribe_live
from translation import detect_language, translate_to_english, translate_from_english
from grammar_correction import correct_grammar
from llm_client import llm

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

    # 🔍 Fetch context and source
    context_text, source_type = answer_query(user_input_en, return_kb_only=True)

    # 📊 Print source info
    print(f"\n📤 Retrieved from: {source_type.upper() if source_type else 'UNKNOWN'}")
    print(f"📚 Context given to LLM:\n{context_text if context_text else '(No context)'}\n")

    # 🧾 Add KB context as system message if it's meaningful
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


def main():
    print("🩷 Welcome to the Breast Cancer Support Assistant 🩷")
    print("You can talk or type. I’ll do my best to help you with info and support.")

    while True:
        mode = input("\n🔄 Type 'voice' for voice input, 'text' to type, or 'exit' to quit: ").strip().lower()

        if mode in ("exit", "bye", "quit"):
            print("👋 Take care! You are not alone. Reach out anytime.")
            sys.exit(0)

        # TEXT MODE
        elif mode == "text":
            print("💬 Text mode activated. Type your message below.")
            print("Type 'back' to return or 'exit' to quit.")
            while True:
                user_input = input("\nYou: ").strip()

                if user_input.lower() in ("back", "b"):
                    conversation_history.clear()

                    break
                if user_input.lower() in ("reset", "new", "clear"):
                    conversation_history.clear()
                    print("🧠 Conversation reset.")
                    continue

                if user_input.lower() in ("exit", "quit", "bye"):
                    print("👋 Stay strong! You're supported.")
                    sys.exit(0)
                if not user_input:
                    print("⚠️ Empty input, please try again.")
                    continue

                reply, lang = process_query(user_input)
                print(f"🤖 Assistant: {reply}")

        # VOICE MODE
        elif mode == "voice":
            print("🎙 Voice mode activated.")
            print("🌐 Choose transcription language mode:")
            print("    👉 Type 'en' for English")
            print("    👉 Type 'ar' for Arabic")
            print("    👉 Type 'auto' for automatic detection")
            lang_mode = input("🌍 Language Mode [en/ar/auto]: ").strip().lower()

            if lang_mode not in ("en", "ar", "auto"):
                print("⚠️ Invalid input. Defaulting to 'auto'.")
                lang_mode = "auto"

            print("🎤 Ready to record. Press ENTER to start recording (5 sec), or type 'back'/'exit'.")
            while True:
                cmd = input(">>> ").strip().lower()
                if cmd in ("back", "b"):
                    break
                if cmd in ("exit", "quit", "bye"):
                    print("👋 Goodbye! You’re not alone.")
                    sys.exit(0)

                if cmd != "":
                    print("⚠️ Press Enter to record, or type 'back'/'exit'.")
                    continue

                try:
                    user_input = transcribe_live(duration=5, forced_lang=lang_mode)
                except Exception as e:
                    print(f"❌ Error transcribing live audio: {e}")
                    continue

                if not user_input.strip():
                    print("⚠️ Couldn’t hear you clearly. Please try again.")
                    continue

                reply, lang = process_query(user_input)
                print(f"🤖 Assistant: {reply}")
# Use the detected language to speak the reply
                if lang not in ["ar", "fr", "en"]:
                    lang = "en"  # fallback

                #text_to_speech(reply, lang=lang)

                print("🎙 Press ENTER to record again, or type 'back'/'exit'.")

        else:
            print("⚠️ Invalid option. Please type 'text', 'voice', or 'exit'.")


if __name__ == "__main__":
    main()
