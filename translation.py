# translation.py
from langdetect import detect
from transformers import pipeline

# Initialize translation pipelines once
en_to_ar = pipeline("translation", model="Helsinki-NLP/opus-mt-en-ar", device=-1)
ar_to_en = pipeline("translation", model="Helsinki-NLP/opus-mt-ar-en", device=-1)
fr_to_en = pipeline("translation", model="Helsinki-NLP/opus-mt-fr-en", device=-1)
en_to_fr = pipeline("translation", model="Helsinki-NLP/opus-mt-en-fr", device=-1)

def detect_language(text):
    try:
        # For very short texts, use some heuristics first
        text_lower = text.lower().strip()
        
        # Common English words that indicate English
        english_indicators = ['hello', 'hi', 'hey', 'what', 'how', 'when', 'where', 'why', 'who', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'have', 'has', 'had', 'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should', 'may', 'might']
        
        # Check if text contains English indicators
        if any(word in text_lower for word in english_indicators):
            print(f"[LANG] Text contains English indicators: {text}")
            return "en"
        
        # Use langdetect for longer texts or when no clear indicators
        lang = detect(text)
        print(f"[LANG] langdetect result: {lang} for text: '{text}'")
        
        # Normalize to base language codes for translation
        if lang and "-" in lang:
            lang = lang.split("-")[0]
        return lang
    except Exception as e:
        print(f"[LANG] Error in language detection: {e}")
        return "en"

def translate_to_english(text, lang):
    # Extract base language code for translation
    base_lang = lang.split("-")[0] if lang and "-" in lang else lang
    
    if base_lang == "ar":
        return ar_to_en(text)[0]['translation_text']
    elif base_lang == "fr":
        return fr_to_en(text)[0]['translation_text']
    return text

def translate_from_english(text, lang):
    # Extract base language code for translation
    base_lang = lang.split("-")[0] if lang and "-" in lang else lang
    
    if base_lang == "ar":
        return en_to_ar(text)[0]['translation_text']
    elif base_lang == "fr":
        return en_to_fr(text)[0]['translation_text']
    return text
