# main.py
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# your existing modules (unchanged workflow)
from query_handler import answer_query
from speech_io import transcribe_audio_file, text_to_speech, transcribe_live
from translation import detect_language, translate_to_english, translate_from_english
from grammar_correction import correct_grammar
from llm_client import llm

load_dotenv()

# ---------------- CONFIG ----------------
ZEP_API_URL = os.getenv("ZEP_API_URL", "https://api.getzep.com")
ZEP_API_KEY = os.getenv("ZEP_API_KEY")  # set in .env
USER_ID = os.getenv("ZEP_USER_ID", "user_123")

LOCAL_FALLBACK = Path("local_zep_fallback.json")

# ---------------- Initialize Zep client (robust) ----------------
zep_client = None
zep_style = None
try:
    # prefer zep_cloud.client if present
    try:
        from zep_cloud.client import Zep as _Zep
        try:
            zep_client = _Zep(api_key=ZEP_API_KEY, base_url=ZEP_API_URL)
            zep_style = "zep_cloud.client(base_url)"
        except TypeError:
            try:
                zep_client = _Zep(api_key=ZEP_API_KEY, url=ZEP_API_URL)
                zep_style = "zep_cloud.client(url)"
            except Exception:
                zep_client = _Zep(api_key=ZEP_API_KEY)
                zep_style = "zep_cloud.client(no url)"
    except Exception:
        # fallback to package named 'zep' (some envs)
        from zep import Zep as _Zep2
        try:
            zep_client = _Zep2(api_key=ZEP_API_KEY, base_url=ZEP_API_URL)
            zep_style = "zep(base_url)"
        except TypeError:
            try:
                zep_client = _Zep2(api_key=ZEP_API_KEY, url=ZEP_API_URL)
                zep_style = "zep(url)"
            except Exception:
                zep_client = _Zep2(api_key=ZEP_API_KEY)
                zep_style = "zep(no url)"
except Exception:
    zep_client = None
    zep_style = None

if zep_client:
    print("✅ Zep client initialized:", zep_style)
else:
    print("⚠️ Zep client not available. Using local fallback storage.")

# ---------------- Local fallback helpers ----------------
def _read_local():
    if not LOCAL_FALLBACK.exists():
        return []
    try:
        return json.loads(LOCAL_FALLBACK.read_text(encoding="utf8"))
    except Exception:
        return []

def _write_local(messages):
    LOCAL_FALLBACK.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf8")

def _append_local(role, content):
    msgs = _read_local()
    msgs.append({"role": role, "content": content})
    _write_local(msgs)

def _clear_local():
    try:
        if LOCAL_FALLBACK.exists():
            LOCAL_FALLBACK.unlink()
            return True
    except Exception:
        pass
    return False

# ---------------- Zep wrapper helpers ----------------
def get_zep_history(user_id=USER_ID):
    """
    Return list of messages [{"role":..., "content":...}, ...] in chronological order.
    Tries a few common zep SDK methods; falls back to local JSON.
    """
    if zep_client:
        # 1) top-level convenience get_memory(user_id)
        try:
            if hasattr(zep_client, "get_memory"):
                raw = zep_client.get_memory(user_id)
                if isinstance(raw, list):
                    return [{"role": (m.get("role") if isinstance(m, dict) else getattr(m, "role", None)),
                             "content": (m.get("content") if isinstance(m, dict) else getattr(m, "content", None))}
                            for m in raw if (isinstance(m, dict) and m.get("role")) or getattr(m, "role", None)]
                if hasattr(raw, "messages"):
                    msgs = getattr(raw, "messages") or []
                    return [{"role": getattr(m, "role", None), "content": getattr(m, "content", None)} for m in msgs if getattr(m, "role", None)]
        except Exception:
            pass

        # 2) memory.get_session_messages(session_id=...)
        try:
            mem = getattr(zep_client, "memory", None)
            if mem and hasattr(mem, "get_session_messages"):
                resp = mem.get_session_messages(session_id=user_id, limit=1000)
                msgs = getattr(resp, "messages", None) or resp or []
                normalized = []
                for m in msgs:
                    role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else None)
                    content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else None)
                    if role and content:
                        normalized.append({"role": role, "content": content})
                return normalized
        except Exception:
            pass

        # 3) memory.get(session_id=...)
        try:
            mem = getattr(zep_client, "memory", None)
            if mem and hasattr(mem, "get"):
                resp = mem.get(session_id=user_id)
                msgs = getattr(resp, "messages", None) or resp or []
                normalized = []
                for m in msgs:
                    role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else None)
                    content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else None)
                    if role and content:
                        normalized.append({"role": role, "content": content})
                return normalized
        except Exception:
            pass

    # fallback to local storage
    local = _read_local()
    return [{"role": m.get("role"), "content": m.get("content")} for m in local]

def save_zep_message(role, content, user_id=USER_ID):
    """
    Save a message (role/content) to Zep (or fallback).
    Returns True on success.
    """
    if zep_client:
        # try top-level convenience add_memory(user_id, role=..., content=...)
        try:
            if hasattr(zep_client, "add_memory"):
                try:
                    zep_client.add_memory(user_id, role=role, content=content)
                    return True
                except Exception:
                    pass
        except Exception:
            pass

        # try mem.add(session_id=..., messages=[{...}])
        try:
            mem = getattr(zep_client, "memory", None)
            if mem and hasattr(mem, "add"):
                mem.add(session_id=user_id, messages=[{"role": role, "content": content}])
                return True
        except Exception:
            pass

        # try mem.create_message or mem.add_message
        try:
            mem = getattr(zep_client, "memory", None)
            if mem:
                for meth in ("add_message", "create_message", "create"):
                    if hasattr(mem, meth):
                        try:
                            getattr(mem, meth)(session_id=user_id, role=role, content=content)
                            return True
                        except Exception:
                            pass
        except Exception:
            pass

    # fallback to local append
    try:
        _append_local(role, content)
        return True
    except Exception:
        return False

def clear_zep_memory(user_id=USER_ID):
    """
    Attempt to clear session memory in Zep. Also clears local fallback.
    Returns True if any clearing succeeded.
    """
    cleared = False
    if zep_client:
        try:
            if hasattr(zep_client, "clear_memory"):
                try:
                    zep_client.clear_memory(user_id)
                    cleared = True
                except Exception:
                    pass
        except Exception:
            pass

        try:
            mem = getattr(zep_client, "memory", None)
            if mem:
                if hasattr(mem, "delete_session"):
                    try:
                        mem.delete_session(session_id=user_id)
                        cleared = True
                    except Exception:
                        pass
                else:
                    # attempt to delete messages by id if possible
                    try:
                        resp = mem.get_session_messages(session_id=user_id, limit=1000)
                        msgs = getattr(resp, "messages", None) or resp or []
                        for m in msgs:
                            mid = getattr(m, "id", None) or (m.get("id") if isinstance(m, dict) else None)
                            if mid and hasattr(mem, "delete_message"):
                                try:
                                    mem.delete_message(message_id=mid)
                                    cleared = True
                                except Exception:
                                    pass
                    except Exception:
                        pass
        except Exception:
            pass

    if _clear_local():
        cleared = True
    return cleared

# ---------------- Keep your workflow but integrate Zep ----------------
def build_history_for_llm():
    """Return conversation list for the LLM in the format [{'role':..., 'content':...}, ...]."""
    msgs = get_zep_history()
    conv = []
    for m in msgs:
        role = (m.get("role") or "").lower()
        content = m.get("content")
        if not role or not content:
            continue
        if role in ("user", "assistant", "system"):
            conv.append({"role": role, "content": content})
        else:
            # normalize unknown role to user (safe)
            if "assist" in role or "bot" in role:
                conv.append({"role": "assistant", "content": content})
            elif "system" in role:
                conv.append({"role": "system", "content": content})
            else:
                conv.append({"role": "user", "content": content})
    return conv

def show_recap():
    msgs = get_zep_history()
    if not msgs:
        print("📝 No conversation history found.")
        return
    print("\n📝 Conversation Recap:")
    for m in msgs:
        role = (m.get("role") or "").lower()
        content = m.get("content", "")
        if role == "user":
            who = "You"
        elif role == "assistant":
            who = "Assistant"
        else:
            who = role.capitalize() or "Unknown"
        print(f"{who}: {content}")
    print("📝 End of recap.\n")

# ---------------- Original process_query with Zep saves ----------------
def process_query(user_input):
    # keep same workflow, but save/load messages from zep/local
    try:
        lang = detect_language(user_input)
        print(f"🌍 Detected language: {lang}")
    except Exception:
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

    # Save user message to Zep/local (store English text for KB consistency)
    saved = save_zep_message("user", user_input_en)
    if not saved:
        print("⚠️ Failed to save user message to Zep/local fallback.")

    # Build conversation history for LLM from Zep/local (so LLM sees past)
    conversation_history = build_history_for_llm()

    # Ensure system prompt present (same behavior as your original code)
    if not any(msg["role"] == "system" for msg in conversation_history):
        conversation_history.insert(0, {
            "role": "system",
            "content": "You are a kind and helpful assistant for breast cancer patients. Answer clearly, supportively, and based on known facts or provided context. If you don’t know, say so."
        })
        # optionally persist system message too
        try:
            save_zep_message("system", conversation_history[0]["content"])
        except Exception:
            pass

    # 🔍 Fetch context and source (unchanged)
    context_text, source_type = answer_query(user_input_en, return_kb_only=True)

    # 📊 Print source info
    print(f"\n📤 Retrieved from: {source_type.upper() if source_type else 'UNKNOWN'}")
    print(f"📚 Context given to LLM:\n{context_text if context_text else '(No context)'}\n")

    # 🧾 Add KB context as system message if meaningful (temporary for LLM input)
    if context_text and source_type not in ["greeting", "not_relevant"]:
        conversation_history.append({
            "role": "system",
            "content": f"Relevant knowledge ({source_type}):\n{context_text}"
        })

    # Call your LLM with the conversation
    try:
        response_en = llm(conversation_history)
    except Exception as e:
        print(f"❌ LLM error: {e}")
        response_en = "Sorry, I encountered an issue answering that."

    # Save assistant response to Zep/local
    saved2 = save_zep_message("assistant", response_en)
    if not saved2:
        print("⚠️ Failed to save assistant message to Zep/local fallback.")

    # Translate back to user's language (unchanged)
    try:
        response_local = translate_from_english(response_en, lang)
    except Exception as e:
        print(f"⚠️ Translation from English failed: {e}")
        response_local = response_en

    return response_local, lang

# ---------------- Main loop (same interaction as your original) ----------------
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
                    # original cleared in-memory conversation; now we clear Zep/local memory
                    ok = clear_zep_memory(USER_ID)
                    if ok:
                        print("🧠 Conversation reset.")
                    else:
                        print("🧠 Local fallback cleared if present.")
                    break
                if user_input.lower() in ("reset", "new", "clear"):
                    ok = clear_zep_memory(USER_ID)
                    if ok:
                        print("🧠 Conversation reset.")
                    else:
                        print("⚠️ Could not clear remote memory; local fallback cleared if present.")
                    continue

                if user_input.lower() in ("exit", "quit", "bye"):
                    print("👋 Stay strong! You're supported.")
                    sys.exit(0)
                if not user_input:
                    print("⚠️ Empty input, please try again.")
                    continue

                # special command to show recap
                if user_input.lower() == "recap":
                    show_recap()
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

                # voice commands
                if user_input.lower() == "recap":
                    show_recap()
                    continue
                if user_input.lower() in ("reset", "new", "clear"):
                    ok = clear_zep_memory(USER_ID)
                    if ok:
                        print("🧠 Conversation reset.")
                    else:
                        print("⚠️ Could not clear remote memory; local fallback cleared if present.")
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
