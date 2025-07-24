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
        return detect(text)
    except:
        return "en"

def translate_to_english(text, lang):
    if lang == "ar":
        return ar_to_en(text)[0]['translation_text']
    elif lang == "fr":
        return fr_to_en(text)[0]['translation_text']
    return text

def translate_from_english(text, lang):
    if lang == "ar":
        return en_to_ar(text)[0]['translation_text']
    elif lang == "fr":
        return en_to_fr(text)[0]['translation_text']
    return text
