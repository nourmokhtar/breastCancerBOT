# speech_io.py
from faster_whisper import WhisperModel
from gtts import gTTS
import sounddevice as sd
import numpy as np
import tempfile
import scipy.io.wavfile
from playsound import playsound
import os

# Initialize Whisper model once
whisper_model = WhisperModel("small", device="cpu")

def transcribe_audio_file(filepath):
    segments, info = whisper_model.transcribe(filepath, beam_size=5)
    full_text = " ".join(segment.text for segment in segments)
    return full_text.strip()


def text_to_speech(text, lang):
    """
    Convert text to speech and play it automatically.
    
    Parameters:
    - text (str): Text to convert to speech.
    - lang (str): Language code (e.g., 'en', 'fr', 'ar').
    
    This function creates a temporary mp3 file, plays it, then deletes it.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tts = gTTS(text=text, lang=lang)
            tts.save(tmp_file.name)
            
            playsound(tmp_file.name)
                
        os.remove(tmp_file.name)
    except Exception as e:
        print(f"⚠️ Text-to-speech error: {e}")

# New function to record from mic and save temporary wav
def record_audio(duration=5, fs=16000):
    print(f"🎙 Recording for {duration} seconds...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    print(f"🎙 DONE...")

    return recording.flatten(), fs

def save_temp_wav(audio_data, fs):
    tmp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    scipy.io.wavfile.write(tmp_file.name, fs, audio_data)
    return tmp_file.name

def transcribe_live(duration=5, forced_lang="auto"):
    audio_data, fs = record_audio(duration)
    wav_path = save_temp_wav(audio_data, fs)

    # Use forced language if provided
    if forced_lang == "auto":
        segments, info = whisper_model.transcribe(wav_path, beam_size=1)
    else:
        segments, info = whisper_model.transcribe(wav_path, beam_size=1, language=forced_lang)

    text = " ".join(segment.text for segment in segments).strip()
    print("📝 Transcribed Text:", text)
    return text
