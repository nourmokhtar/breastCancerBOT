from gtts import gTTS
from gtts.lang import tts_langs
import os

# Preload supported language codes from gTTS
GTTS_LANGS = tts_langs()

def pick_tld_for_accent(lang_code: str) -> str:
    """Choose a gTTS tld to better match accent when possible.
    This is a best-effort mapping for common cases.
    """
    code = (lang_code or "en").lower()
    region = ""
    if "-" in code:
        code, region = code.split("-", 1)

    print(f"[TTS] Picking TLD for: code='{code}', region='{region}'")

    # English regional accents
    if code == "en":
        if region in ("gb", "uk"):  # British English
            return "co.uk"
        if region == "au":  # Australian English
            return "com.au"
        if region == "in":  # Indian English
            return "co.in"
        if region == "ie":  # Irish English
            return "ie"
        if region == "za":  # South African English
            return "co.za"
        if region == "ng":  # Nigerian English
            return "com.ng"
        if region == "ca":  # Canadian English
            return "ca"
        if region == "ph":  # Philippine English
            return "com.ph"
        # Default to US/International
        return "com"

    # French regional accents
    if code == "fr":
        if region == "ca":  # Canadian French
            return "ca"
        if region == "fr":  # French French
            return "com"
        if region == "be":  # Belgian French
            return "com"
        if region == "ch":  # Swiss French
            return "com"
        return "com"  # default

    # Spanish regional accents
    if code == "es":
        if region == "mx":  # Mexican Spanish
            return "com.mx"
        if region == "ar":  # Argentine Spanish
            return "com.ar"
        if region == "cl":  # Chilean Spanish
            return "cl"
        if region == "co":  # Colombian Spanish
            return "com.co"
        if region == "pe":  # Peruvian Spanish
            return "com.pe"
        if region == "ve":  # Venezuelan Spanish
            return "com.ve"
        if region == "es":  # Spanish Spanish
            return "com"
        return "com"  # safe default

    # Portuguese regional accents
    if code == "pt":
        if region == "br":  # Brazilian Portuguese
            return "com.br"
        if region == "pt":  # European Portuguese
            return "pt"
        return "com"

    # Arabic regional accents
    if code == "ar":
        if region == "sa":  # Saudi Arabic
            return "com"
        if region == "eg":  # Egyptian Arabic
            return "com"
        if region == "ma":  # Moroccan Arabic
            return "com"
        if region == "dz":  # Algerian Arabic
            return "com"
        if region == "tn":  # Tunisian Arabic
            return "com"
        return "com"

    # German regional accents
    if code == "de":
        if region == "de":  # German German
            return "com"
        if region == "at":  # Austrian German
            return "com"
        if region == "ch":  # Swiss German
            return "com"
        return "com"

    # Italian regional accents
    if code == "it":
        if region == "it":  # Italian Italian
            return "com"
        if region == "ch":  # Swiss Italian
            return "com"
        return "com"

    # Default for other languages
    return "com"

def get_gtts_lang(whisper_code):
    """
    Normalize Whisper/ISO code to a lang supported by gTTS.
    Falls back to 'en' when unsupported.
    """
    if not whisper_code:
        return "en"
    
    code = whisper_code.lower()
    print(f"[TTS] Normalizing language code: '{whisper_code}' -> '{code}'")
    
    # Direct mapping for common Whisper codes
    whisper_to_gtts = {
        # English variants
        "en": "en",
        "en-us": "en",
        "en-gb": "en",
        "en-au": "en",
        "en-in": "en",
        "en-ca": "en",
        "en-ie": "en",
        "en-za": "en",
        "en-ng": "en",
        "en-ph": "en",
        
        # French variants
        "fr": "fr",
        "fr-ca": "fr",
        "fr-fr": "fr",
        "fr-be": "fr",
        "fr-ch": "fr",
        
        # Spanish variants
        "es": "es",
        "es-mx": "es",
        "es-ar": "es",
        "es-cl": "es",
        "es-co": "es",
        "es-pe": "es",
        "es-ve": "es",
        "es-es": "es",
        
        # Arabic variants
        "ar": "ar",
        "ar-sa": "ar",
        "ar-eg": "ar",
        "ar-ma": "ar",
        "ar-dz": "ar",
        "ar-tn": "ar",
        
        # Italian
        "it": "it",
        "it-it": "it",
        "it-ch": "it",
        
        # German
        "de": "de",
        "de-de": "de",
        "de-at": "de",
        "de-ch": "de",
        
        # Portuguese
        "pt": "pt",
        "pt-br": "pt",
        "pt-pt": "pt",
        
        # Dutch
        "nl": "nl",
        "nl-nl": "nl",
        "nl-be": "nl",
        
        # Russian
        "ru": "ru",
        "ru-ru": "ru",
        
        # Chinese
        "zh": "zh",
        "zh-cn": "zh",
        "zh-tw": "zh",
        "zh-hk": "zh",
        
        # Japanese
        "ja": "ja",
        "ja-jp": "ja",
        
        # Korean
        "ko": "ko",
        "ko-kr": "ko",
        
        # Hindi
        "hi": "hi",
        "hi-in": "hi",
        
        # Bengali
        "bn": "bn",
        "bn-bd": "bn",
        "bn-in": "bn",
        
        # Turkish
        "tr": "tr",
        "tr-tr": "tr",
        
        # Polish
        "pl": "pl",
        "pl-pl": "pl",
        
        # Swedish
        "sv": "sv",
        "sv-se": "sv",
        
        # Norwegian
        "no": "no",
        "nb": "no",  # Norwegian Bokmål
        "nn": "no",  # Norwegian Nynorsk
        
        # Danish
        "da": "da",
        "da-dk": "da",
        
        # Finnish
        "fi": "fi",
        "fi-fi": "fi",
        
        # Greek
        "el": "el",
        "el-gr": "el",
        
        # Hebrew
        "he": "he",
        "he-il": "he",
        
        # Thai
        "th": "th",
        "th-th": "th",
        
        # Vietnamese
        "vi": "vi",
        "vi-vn": "vi",
        
        # Indonesian
        "id": "id",
        "id-id": "id",
        
        # Malay
        "ms": "ms",
        "ms-my": "ms",
        
        # Filipino/Tagalog
        "tl": "tl",
        "fil": "tl",
        
        # Ukrainian
        "uk": "uk",
        "uk-ua": "uk",
        
        # Czech
        "cs": "cs",
        "cs-cz": "cs",
        
        # Hungarian
        "hu": "hu",
        "hu-hu": "hu",
        
        # Romanian
        "ro": "ro",
        "ro-ro": "ro",
        
        # Bulgarian
        "bg": "bg",
        "bg-bg": "bg",
        
        # Croatian
        "hr": "hr",
        "hr-hr": "hr",
        
        # Serbian
        "sr": "sr",
        "sr-rs": "sr",
        
        # Slovak
        "sk": "sk",
        "sk-sk": "sk",
        
        # Slovenian
        "sl": "sl",
        "sl-si": "sl",
        
        # Estonian
        "et": "et",
        "et-ee": "et",
        
        # Latvian
        "lv": "lv",
        "lv-lv": "lv",
        
        # Lithuanian
        "lt": "lt",
        "lt-lt": "lt",
    }
    
    # Check direct mapping first
    if code in whisper_to_gtts:
        gtts_code = whisper_to_gtts[code]
        if gtts_code in GTTS_LANGS:
            print(f"[TTS] Direct mapping: '{code}' -> '{gtts_code}'")
            return gtts_code
    
    # Fallback: try the base language code
    if code in GTTS_LANGS:
        print(f"[TTS] Direct gTTS support: '{code}'")
        return code
    
    # Fallback: try to extract base language from regional code
    if "-" in code:
        base_lang = code.split("-", 1)[0]
        if base_lang in GTTS_LANGS:
            print(f"[TTS] Base language fallback: '{code}' -> '{base_lang}'")
            return base_lang
    
    # Final fallback to English
    print(f"[TTS] Final fallback to English for: '{code}'")
    return "en"

def synthesize_speech(text, lang_code="en", output_path="static/llm_response.mp3"):
    """
    Synthesize speech with improved language and accent handling.
    
    Args:
        text: Text to synthesize
        lang_code: Language code (can be Whisper format like 'en-us', 'fr-ca', etc.)
        output_path: Output file path
    """
    print(f"[TTS] Starting synthesis for text: '{text[:50]}...' with lang_code: '{lang_code}'")
    
    lang = get_gtts_lang(lang_code)
    tld = pick_tld_for_accent(lang_code)
    
    print(f"[TTS] Final settings - gTTS language: {lang}, TLD: {tld}")
    
    try:
        tts = gTTS(text=text, lang=lang, tld=tld)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        # Always save as mp3; if caller passes .wav, file will still be mp3 content.
        if not output_path.lower().endswith(".mp3"):
            output_path = os.path.splitext(output_path)[0] + ".mp3"
        
        tts.save(output_path)
        print(f"[TTS] Successfully saved audio to: {output_path}")
        return os.path.basename(output_path)
        
    except Exception as e:
        print(f"[TTS] Error with language {lang} and tld {tld}: {e}")
        # Fallback to English if the selected language fails
        if lang != "en":
            print(f"[TTS] Falling back to English...")
            try:
                tts = gTTS(text=text, lang="en", tld="com")
                tts.save(output_path)
                print(f"[TTS] Fallback successful")
                return os.path.basename(output_path)
            except Exception as fallback_error:
                print(f"[TTS] Fallback also failed: {fallback_error}")
                raise fallback_error
        else:
            raise e
