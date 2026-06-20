from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0

def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        if lang == "kn":
            return "kn"
        elif lang == "hi":
            return "hi"
        else:
            return "en"
    except Exception:
        return "en"
