import language_tool_python
from spellchecker import SpellChecker
import re

def normalize_arabic(text: str) -> str:
    # Remove diacritics (Tashkeel)
    diacritics = re.compile("""
         ّ    | # Shadda
         َ    | # Fatha
         ً    | # Tanwin Fath
         ُ    | # Damma
         ٌ    | # Tanwin Damm
         ِ    | # Kasra
         ٍ    | # Tanwin Kasr
         ْ    | # Sukun
         ـ     # Tatwil/Kashida
     """, re.VERBOSE)
    text = re.sub(diacritics, '', text)

    # Normalize Alef variants
    text = re.sub("[إأآا]", "ا", text)
    # Normalize Yeh
    text = re.sub("[يى]", "ي", text)
    # Normalize Teh Marbuta to Heh
    text = re.sub("ة", "ه", text)
    # Normalize Tatweel
    text = re.sub("ـ", "", text)

    # Remove non-Arabic letters (optional)
    text = re.sub(r'[^\u0600-\u06FF\s]', '', text)

    # Remove extra spaces
    text = re.sub('\s+', ' ', text).strip()

    return text


# English and French spell checkers
spell_en = SpellChecker(language='en')
spell_fr = SpellChecker(language='fr')

def fix_spelling(text: str, lang: str) -> str:
    if lang not in ['en', 'fr']:
        return text  # No fix for Arabic or others

    spell = spell_en if lang == 'en' else spell_fr
    words = text.split()
    corrected_words = []

    for word in words:
        if word.lower() in spell:
            corrected_words.append(word)
        else:
            corrected = spell.correction(word)
            corrected_words.append(corrected if corrected else word)

    return ' '.join(corrected_words)

tool = language_tool_python.LanguageTool('en-US')

def correct_grammar(text: str, lang: str) -> str:
    if lang in ['en', 'fr']:
        return fix_spelling(text, lang)
    elif lang == 'ar':
        return normalize_arabic(text)
    else:
        return text