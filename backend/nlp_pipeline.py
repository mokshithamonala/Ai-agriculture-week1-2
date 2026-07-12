import os
import re
from typing import Dict, List, Tuple, Any

# Try loading Hugging Face components, fallback to rule-based/API if they fail or packages are missing
HF_AVAILABLE = False
try:
    from transformers import pipeline
    HF_AVAILABLE = True
except ImportError:
    print("NLP Pipeline Warning: transformers/torch not available. Using lightweight fallbacks.")

# Try importing langdetect
LANGDETECT_AVAILABLE = False
try:
    import langdetect
    langdetect.DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    print("NLP Pipeline Warning: langdetect not available. Using regex language detection.")

# Local lookup dictionaries for agricultural entities
AGRI_KEYWORDS = {
    "crops": ["wheat", "rice", "paddy", "cotton", "maize", "tomato", "potato", "onion", "chilli", "groundnut", "mustard", "soybean", "sugarcane", "gram", "bajra"],
    "pests": ["whitefly", "aphids", "stem borer", "leaf spot", "rust", "rot", "blight", "caterpillar", "mites", "locust", "fungus", "weevil", "armyworm"],
    "fertilizers": ["urea", "potash", "npk", "compost", "manure", "phosphate", "nitrogen", "potassium", "gypsum", "ammonium sulfate", "dap"],
    "soilTypes": ["clay", "sandy", "loam", "black soil", "red soil", "alluvial", "acidic", "alkaline", "silt"],
    "weather": ["rain", "monsoon", "temperature", "humidity", "drought", "storm", "frost", "wind", "hail", "cold", "heatwave"],
    "schemes": ["pm kisan", "crop insurance", "fasal bima", "kcc", "kisan credit card", "subsidy", "rythu bharosa", "krishi sinchayee"]
}

# Mapping of labels to target intents
INTENTS = [
    "Crop Advisory",
    "Pest Management",
    "Soil Health",
    "Irrigation",
    "Weather",
    "Government Schemes",
    "General Agriculture"
]

# Lazy load Hugging Face pipelines to speed up startup and catch failures
_lang_classifier = None
_intent_classifier = None

def get_hf_classifiers():
    global _lang_classifier, _intent_classifier, HF_AVAILABLE
    if not HF_AVAILABLE:
        return None, None
        
    try:
        # Load a small language detector or pipeline
        if _lang_classifier is None:
            # Using a tiny sentiment pipeline just to show HF transformers integration if needed,
            # or a tiny language identifier if download is fast.
            # We use cardiffnlp/twitter-roberta-base-sentiment-latest or similar small model.
            # However, langdetect is the primary local language detector for speed.
            print("NLP Pipeline: Loading Hugging Face models...")
            _lang_classifier = pipeline("text-classification", model="papluca/xlm-roberta-base-language-detection", device=-1)
            
        if _intent_classifier is None:
            # Zero-shot classification pipeline for intent prediction
            _intent_classifier = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli", device=-1)
            
        return _lang_classifier, _intent_classifier
    except Exception as e:
        print(f"NLP Pipeline Error: Failed to load Hugging Face models ({e}). Falling back to local/API rules.")
        HF_AVAILABLE = False
        return None, None

def detect_language(text: str) -> str:
    """Detects if language is English ('en'), Hindi ('hi'), or Kannada ('kn')."""
    if not text or not text.strip():
        return "en"
        
    # Unicode range checks as a fast, high-confidence filter
    # Devanagari range for Hindi
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"
    # Kannada range
    if re.search(r"[\u0c80-\u0cff]", text):
        return "kn"
        
    # Fallback to langdetect library if available
    if LANGDETECT_AVAILABLE:
        try:
            detected = langdetect.detect(text)
            if detected in ["hi", "kn", "en"]:
                return detected
        except Exception:
            pass

    # Try Hugging Face pipeline if loaded
    if HF_AVAILABLE:
        try:
            lang_pipe, _ = get_hf_classifiers()
            if lang_pipe:
                res = lang_pipe(text[:100])[0]
                label = res['label'].lower()
                if 'hindi' in label or label == 'hi':
                    return 'hi'
                elif 'kannada' in label or label == 'kn':
                    return 'kn'
                elif 'english' in label or label == 'en':
                    return 'en'
        except Exception:
            pass
            
    # Default to english
    return "en"

def classify_intent_local(query: str) -> str:
    """Classifies user intent based on agricultural vocabulary keywords."""
    query_lower = query.lower()
    
    if any(x in query_lower for x in AGRI_KEYWORDS["pests"]) or any(x in query_lower for x in ["disease", "spray", "insect", "cure", "kill", "infestation", "rot", "blight"]):
        return "Pest Management"
    elif any(x in query_lower for x in AGRI_KEYWORDS["fertilizers"]) or any(x in query_lower for x in AGRI_KEYWORDS["soilTypes"]) or any(x in query_lower for x in ["soil", "earth", "nutrient", "compost", "manure", "nitrogen", "ph"]):
        return "Soil Health"
    elif any(x in query_lower for x in ["water", "irrigation", "drip", "borewell", "pump", "sprinkler", "canal", "watering", "flow"]):
        return "Irrigation"
    elif any(x in query_lower for x in AGRI_KEYWORDS["schemes"]) or any(x in query_lower for x in ["scheme", "yojana", "loan", "insurance", "subsidy", "money", "claim", "pm-kisan"]):
        return "Government Schemes"
    elif any(x in query_lower for x in AGRI_KEYWORDS["weather"]) or any(x in query_lower for x in ["rain", "monsoon", "weather", "temperature", "forecast", "climate"]):
        return "Weather"
    elif any(x in query_lower for x in AGRI_KEYWORDS["crops"]) or any(x in query_lower for x in ["seed", "sow", "grow", "harvest", "yield", "planting", "season"]):
        return "Crop Advisory"
        
    return "General Agriculture"

def classify_intent(query: str) -> str:
    """Classifies intent using Hugging Face Zero-Shot Classification, falling back to local lookup."""
    query_lower = query.lower()
    
    # Try zero-shot pipeline if HF is available and successfully loaded
    if HF_AVAILABLE:
        try:
            _, intent_pipe = get_hf_classifiers()
            if intent_pipe:
                result = intent_pipe(query, candidate_labels=INTENTS)
                return result['labels'][0]
        except Exception as e:
            print(f"Zero-shot classification error: {e}")
            
    # Local fallback matching
    return classify_intent_local(query)

def extract_entities(query: str) -> Dict[str, List[str]]:
    """Extracts agricultural entities (crops, pests, soil types, etc.) from the query."""
    query_lower = query.lower()
    entities = {
        "crops": [],
        "pests": [],
        "fertilizers": [],
        "soilTypes": [],
        "weather": [],
        "schemes": []
    }
    
    for category, keywords in AGRI_KEYWORDS.items():
        for keyword in keywords:
            # Use boundaries to prevent matching sub-words (e.g. "rain" in "grain")
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, query_lower):
                entities[category].append(keyword)
                
    return entities
