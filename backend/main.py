import os
import base64
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.local"))

# Import sqlite database & knowledge base layers
from data_layer import db_instance, kb_instance

app = FastAPI(
    title="Kisan Sahayak API",
    description="Multilingual Agricultural Advisory System NLP & Speech Engine",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request validation schemas
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = []
    language: Optional[str] = "en"
    sessionId: Optional[str] = "session-default"
    mode: Optional[str] = "text"

class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "en"

# NLP Manager class handling Language Detection, Intent Classification, and NER
class NLPManager:
    @staticmethod
    def parse_local_nlp(text: str) -> Tuple[str, Dict[str, List[str]]]:
        """Local Rule-Based Fallback Parser (Offline, zero dependencies, zero disk space)."""
        query = text.lower()
        
        agri_keywords = {
            "crops": ["wheat", "rice", "paddy", "cotton", "maize", "tomato", "potato", "onion", "chilli", "groundnut", "soybean", "gram", "pulse", "cereal"],
            "pests": ["whitefly", "aphids", "stem borer", "leaf spot", "rust", "rot", "blight", "caterpillar", "mites", "insect", "bug", "fungus"],
            "fertilizers": ["urea", "potash", "npk", "compost", "manure", "phosphate", "nitrogen", "potassium", "dap"],
            "soilTypes": ["clay", "sandy", "loam", "black soil", "red soil", "alluvial", "soil"],
            "weather": ["rain", "monsoon", "temperature", "humidity", "drought", "storm", "frost", "cold", "hot"],
            "schemes": ["pm kisan", "crop insurance", "fasal bima", "kcc", "kisan credit card", "subsidy", "yojana"]
        }
        
        entities = {
            "crops": [], "pests": [], "fertilizers": [],
            "soilTypes": [], "weather": [], "schemes": []
        }
        
        for category, words in agri_keywords.items():
            for word in words:
                if word in query:
                    entities[category].append(word)
                    
        # Classify Intent
        intent = "General Agriculture"
        if entities["pests"] or any(x in query for x in ["disease", "spray", "insect", "cure", "kill", "pest"]):
            intent = "Pest Management"
        elif entities["fertilizers"] or entities["soilTypes"] or any(x in query for x in ["soil", "earth", "nutrient", "compost"]):
            intent = "Soil Health"
        elif any(x in query for x in ["water", "irrigation", "drip", "borewell", "pump", "sprinkler", "channel"]):
            intent = "Irrigation"
        elif entities["schemes"] or any(x in query for x in ["scheme", "yojana", "loan", "insurance", "subsidy", "money", "claim"]):
            intent = "Government Schemes"
        elif any(x in query for x in ["weather", "rain", "temperature", "forecast", "monsoon"]):
            intent = "Weather"
        elif entities["crops"] or any(x in query for x in ["seed", "sow", "grow", "harvest", "yield", "variety"]):
            intent = "Crop Advisory"
            
        return intent, entities

    @staticmethod
    def query_hf_intent(text: str, hf_key: Optional[str] = None) -> Optional[str]:
        """Queries Hugging Face Serverless Inference API for Agricultural Intent Classification."""
        labels = [
            "Crop Advisory", "Pest Management", "Soil Health", 
            "Irrigation", "Weather", "Government Schemes", "General Agriculture"
        ]
        try:
            url = "https://api-inference.huggingface.co/models/cross-encoder/nli-distilroberta-base"
            headers = {}
            if hf_key:
                headers["Authorization"] = f"Bearer {hf_key}"
            payload = {
                "inputs": text,
                "parameters": {"candidate_labels": labels}
            }
            response = requests.post(url, headers=headers, json=payload, timeout=7)
            if response.status_code == 200:
                data = response.json()
                if "labels" in data and len(data["labels"]) > 0:
                    return data["labels"][0]
        except Exception as e:
            print(f"Hugging Face Intent inference exception: {e}")
        return None

    @staticmethod
    def query_openai_parser(text: str, openai_key: str) -> Optional[Tuple[str, Dict[str, List[str]]]]:
        """Queries OpenAI API to perform joint Language Detection, Intent Classification, and NER."""
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            prompt = (
                "You are an AI Agricultural Parser. Analyze the following farmer query.\n"
                f"Query: \"{text}\"\n\n"
                "Return a JSON object containing:\n"
                "1. \"detected_language\": Must be either \"en\", \"hi\", or \"kn\".\n"
                "2. \"intent\": Must be one of the following: \"Crop Advisory\", \"Pest Management\", \"Soil Health\", \"Irrigation\", \"Weather\", \"Government Schemes\", \"General Agriculture\".\n"
                "3. \"entities\": A dictionary containing lists of words found in the query for: \"crops\", \"pests\", \"fertilizers\", \"soilTypes\", \"weather\", \"schemes\". Only output empty arrays if none match.\n\n"
                "Respond ONLY with valid JSON. Do not include markdown codeblocks (e.g. ```json) or explanation."
            )
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                res_data = response.json()["choices"][0]["message"]["content"]
                parsed = json.loads(res_data)
                
                intent = parsed.get("intent", "General Agriculture")
                entities = parsed.get("entities", {
                    "crops": [], "pests": [], "fertilizers": [],
                    "soilTypes": [], "weather": [], "schemes": []
                })
                # Ensure all entity lists are present
                for key in ["crops", "pests", "fertilizers", "soilTypes", "weather", "schemes"]:
                    if key not in entities:
                        entities[key] = []
                return intent, entities
        except Exception as e:
            print(f"OpenAI Joint Parsing exception: {e}")
        return None

    @staticmethod
    def query_groq_parser(text: str, groq_key: str) -> Optional[Tuple[str, Dict[str, List[str]]]]:
        """Queries Groq API to perform joint Language Detection, Intent Classification, and NER."""
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            prompt = (
                "You are an AI Agricultural Parser. Analyze the following farmer query.\n"
                f"Query: \"{text}\"\n\n"
                "Return a JSON object containing:\n"
                "1. \"detected_language\": Must be either \"en\", \"hi\", or \"kn\".\n"
                "2. \"intent\": Must be one of the following: \"Crop Advisory\", \"Pest Management\", \"Soil Health\", \"Irrigation\", \"Weather\", \"Government Schemes\", \"General Agriculture\".\n"
                "3. \"entities\": A dictionary containing lists of words found in the query for: \"crops\", \"pests\", \"fertilizers\", \"soilTypes\", \"weather\", \"schemes\". Only output empty arrays if none match.\n\n"
                "Respond ONLY with valid JSON. Do not include markdown codeblocks (e.g. ```json) or explanation."
            )
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                res_data = response.json()["choices"][0]["message"]["content"]
                parsed = json.loads(res_data)
                
                intent = parsed.get("intent", "General Agriculture")
                entities = parsed.get("entities", {
                    "crops": [], "pests": [], "fertilizers": [],
                    "soilTypes": [], "weather": [], "schemes": []
                })
                # Ensure all entity lists are present
                for key in ["crops", "pests", "fertilizers", "soilTypes", "weather", "schemes"]:
                    if key not in entities:
                        entities[key] = []
                return intent, entities
        except Exception as e:
            print(f"Groq Joint Parsing exception: {e}")
        return None

# Translation Helpers
def sarvam_translate(text: str, source_lang: str, target_lang: str, api_key: str) -> Optional[str]:
    try:
        url = "https://api.sarvam.ai/translate"
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }
        src = f"{source_lang}-IN" if source_lang != "en" else "en-IN"
        tgt = f"{target_lang}-IN" if target_lang != "en" else "en-IN"
        
        payload = {
            "input": text,
            "source_language_code": src,
            "target_language_code": tgt,
            "model": "sarvam-translate:v1"
        }
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json().get("translated_text")
    except Exception as e:
        print(f"Sarvam translate exception: {e}")
    return None

def openai_translate(text: str, source_lang: str, target_lang: str, api_key: str) -> Optional[str]:
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # Provide specific translation details
        prompt = (
            f"Translate the following agricultural query or advice from {source_lang} to {target_lang}. "
            "Maintain the tone and agricultural terms. Respond ONLY with the translation: "
            f"\"{text}\""
        )
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip().strip('"')
    except Exception as e:
        print(f"OpenAI translate exception: {e}")
    return None

def groq_translate(text: str, source_lang: str, target_lang: str, api_key: str) -> Optional[str]:
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        prompt = (
            f"Translate the following agricultural query or advice from {source_lang} to {target_lang}. "
            "Maintain the tone and agricultural terms. Respond ONLY with the translation: "
            f"\"{text}\""
        )
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip().strip('"')
    except Exception as e:
        print(f"Groq translate exception: {e}")
    return None

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    openai_key = os.getenv("OPENAI_API_KEY")
    sarvam_key = os.getenv("SARVAM_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    hf_key = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_API_KEY")
    
    language = request.language or "en"
    session_id = request.sessionId or "session-default"
    
    # 1. Translate incoming query to canonical English for internal NLP & RAG processing
    english_query = request.message
    if language != "en":
        translated = None
        if sarvam_key:
            translated = sarvam_translate(request.message, language, "en", sarvam_key)
        if not translated and groq_key:
            translated = groq_translate(request.message, language, "en", groq_key)
        if not translated and openai_key:
            translated = openai_translate(request.message, language, "en", openai_key)
        if translated:
            english_query = translated
            
    # 2. Get past entities context from SQLite database to preserve conversational state
    context_entities = db_instance.get_last_entities_context(session_id)
    
    # 3. Multilingual NLP Pipeline: Intent & Entity Classification
    intent = None
    entities = None
    
    # Attempt Primary 0: Groq Joint Parser
    if groq_key:
        parsed_result = NLPManager.query_groq_parser(english_query, groq_key)
        if parsed_result:
            intent, entities = parsed_result
            
    # Attempt Primary A: OpenAI Joint Parser (most accurate for multilingual NER)
    if not intent and openai_key:
        parsed_result = NLPManager.query_openai_parser(english_query, openai_key)
        if parsed_result:
            intent, entities = parsed_result
            
    # Attempt Primary B: Hugging Face Serverless Inference API (Zero-Shot Classification)
    if not intent and hf_key:
        hf_intent = NLPManager.query_hf_intent(english_query, hf_key)
        if hf_intent:
            intent = hf_intent
            # Use local regex parser for NER mapping
            _, entities = NLPManager.parse_local_nlp(english_query)
            
    # Fallback Tertiary: Local Regex Parser (offline, zero external hits)
    if not intent or not entities:
        local_intent, local_entities = NLPManager.parse_local_nlp(english_query)
        intent = intent or local_intent
        entities = entities or local_entities

    # Merge newly detected entities with previous conversational history context
    for cat in context_entities.keys():
        context_entities[cat] = list(set(context_entities[cat] + entities.get(cat, [])))

    # Save User message in DB
    db_instance.save_message(
        session_id=session_id,
        msg_id=f"user-{datetime.now().timestamp()}",
        sender="user",
        text=request.message,
        intent=intent,
        entities=entities
    )

    # 4. RAG / KB Retrieval Step
    kb_content = kb_instance.retrieve_info(intent, context_entities, english_query)

    # 5. Formulate final English answer
    english_answer = kb_content
    generated_answer = False
    
    if groq_key:
        try:
            # Build history list for Llama-3.3-70b-versatile
            past_messages = db_instance.get_session_history(session_id, limit=8)
            formatted_history = []
            for m in past_messages[:-1]: # Exclude the user message we just inserted
                role = "user" if m["sender"] == "user" else "assistant"
                formatted_history.append({"role": role, "content": m["text"]})
            
            system_prompt = (
                "You are Kisan Sahayak, an expert agricultural AI assistant helping farmers with crop advisory, soil health, and pest management.\n"
                "Explain agricultural instructions in a clear, friendly, and structured manner suited for farmers.\n"
                "Use the official guidelines provided below. If they contain the answer, prioritize them. If not, use your general knowledge to supply a correct, helpful, and safe farming answer.\n"
                f"Official Agricultural Guidelines:\n{kb_content}"
            )
            
            messages = [{"role": "system", "content": system_prompt}] + formatted_history + [{"role": "user", "content": english_query}]
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 500
            }
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                english_answer = response.json()["choices"][0]["message"]["content"].strip()
                generated_answer = True
        except Exception as e:
            print(f"Groq conversational completion failed: {e}")

    if not generated_answer and openai_key:
        try:
            # Build history list for GPT-4o-mini
            past_messages = db_instance.get_session_history(session_id, limit=8)
            formatted_history = []
            for m in past_messages[:-1]: # Exclude the user message we just inserted
                role = "user" if m["sender"] == "user" else "assistant"
                formatted_history.append({"role": role, "content": m["text"]})
            
            system_prompt = (
                "You are Kisan Sahayak, an expert agricultural AI assistant helping farmers with crop advisory, soil health, and pest management.\n"
                "Explain agricultural instructions in a clear, friendly, and structured manner suited for farmers.\n"
                "Use the official guidelines provided below. If they contain the answer, prioritize them. If not, use your general knowledge to supply a correct, helpful, and safe farming answer.\n"
                f"Official Agricultural Guidelines:\n{kb_content}"
            )
            
            messages = [{"role": "system", "content": system_prompt}] + formatted_history + [{"role": "user", "content": english_query}]
            
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.4,
                "max_tokens": 500
            }
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                english_answer = response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"OpenAI conversational completion failed: {e}")

    # 6. Translate response back to original farmer language
    final_response = english_answer
    if language != "en":
        translated_back = None
        if sarvam_key:
            translated_back = sarvam_translate(english_answer, "en", language, sarvam_key)
        if not translated_back and groq_key:
            translated_back = groq_translate(english_answer, "en", language, groq_key)
        if not translated_back and openai_key:
            translated_back = openai_translate(english_answer, "en", language, openai_key)
        if translated_back:
            final_response = translated_back

    # Save Assistant Response in SQLite DB
    db_instance.save_message(
        session_id=session_id,
        msg_id=f"assistant-{datetime.now().timestamp()}",
        sender="assistant",
        text=final_response,
        intent=intent,
        entities=entities
    )

    return {
        "original_query": request.message,
        "translated_query": english_query,
        "response": final_response,
        "intent": intent,
        "entities": entities,
        "session_id": session_id,
        "mode": request.mode
    }

@app.post("/api/stt")
async def speech_to_text(file: UploadFile = File(...), language: str = Form("en")):
    sarvam_key = os.getenv("SARVAM_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    
    audio_bytes = await file.read()
    
    # Primary: Groq Whisper STT (extremely fast and supports multilingual speech-to-text)
    if groq_key:
        try:
            url = "https://api.groq.com/openai/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {groq_key}"}
            files = {
                "file": ("audio.webm", audio_bytes, "audio/webm")
            }
            data = {
                "model": "whisper-large-v3",
                "language": language
            }
            response = requests.post(url, headers=headers, files=files, data=data, timeout=15)
            if response.status_code == 200:
                transcript = response.json().get("text", "")
                if transcript.strip():
                    return {"transcript": transcript, "provider": "groq"}
        except Exception as e:
            print(f"Groq Whisper STT failed: {e}")
            
    # Fallback B: Sarvam AI STT (optimized for Indian languages like Hindi & Kannada)
    if sarvam_key and language in ["hi", "kn"]:
        try:
            url = "https://api.sarvam.ai/speech-to-text"
            headers = {"api-subscription-key": sarvam_key}
            sarvam_lang = "hi-IN" if language == "hi" else "kn-IN"
            
            files = {
                "file": ("audio.webm", audio_bytes, "audio/webm")
            }
            data = {
                "model": "saaras:v3",
                "language_code": sarvam_lang,
                "mode": "transcribe"
            }
            
            response = requests.post(url, headers=headers, files=files, data=data, timeout=15)
            if response.status_code == 200:
                transcript = response.json().get("transcript", "")
                if transcript.strip():
                    return {"transcript": transcript, "provider": "sarvam"}
        except Exception as e:
            print(f"Sarvam STT failed: {e}")
            
    # Fallback C: OpenAI Whisper STT
    if openai_key:
        try:
            url = "https://api.openai.com/v1/audio/transcriptions"
            headers = {"Authorization": f"Bearer {openai_key}"}
            files = {
                "file": ("audio.webm", audio_bytes, "audio/webm")
            }
            data = {
                "model": "whisper-1",
                "language": language
            }
            response = requests.post(url, headers=headers, files=files, data=data, timeout=15)
            if response.status_code == 200:
                transcript = response.json().get("text", "")
                if transcript.strip():
                    return {"transcript": transcript, "provider": "openai"}
        except Exception as e:
            print(f"OpenAI Whisper STT failed: {e}")
            
    # If all premium cloud APIs fail/are missing, return 503 so frontend initiates browser SpeechRecognition fallback
    raise HTTPException(status_code=503, detail="Server STT service temporarily unavailable. Falling back to browser speech engine.")

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    sarvam_key = os.getenv("SARVAM_API_KEY")
    
    # Primary: Sarvam AI Text-to-Speech (native accents for Kannada and Hindi)
    if sarvam_key:
        try:
            url = "https://api.sarvam.ai/text-to-speech"
            headers = {
                "api-subscription-key": sarvam_key,
                "Content-Type": "application/json"
            }
            sarvam_lang = "hi-IN" if request.language == "hi" else "kn-IN" if request.language == "kn" else "en-IN"
            
            payload = {
                "text": request.text,
                "target_language_code": sarvam_lang,
                "model": "bulbul:v3",
                "speaker": "meera"
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                audios = response.json().get("audios", [])
                if audios and len(audios) > 0:
                    return {"audio": audios[0], "provider": "sarvam"}
        except Exception as e:
            print(f"Sarvam TTS failed: {e}")
            
    # Return 503 so frontend automatically utilizes browser SpeechSynthesis fallback
    raise HTTPException(status_code=503, detail="Server TTS service unavailable. Falling back to browser synthesis.")

@app.get("/api/health")
async def health_check():
    sarvam_key = os.getenv("SARVAM_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "has_stt": bool(sarvam_key or openai_key or groq_key),
        "has_tts": bool(sarvam_key)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
