import os
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime

# Locate SQLite Database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "advisory.db")

class AdvisoryDB:
    """
    SQLite persistence layer for storing session configurations, user preferences,
    and chat history, ensuring conversational context and follow-up query continuity.
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Session Configuration store
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    language TEXT NOT NULL,
                    user_preferences TEXT, -- JSON structure
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # Chat history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sender TEXT NOT NULL, -- 'user' or 'assistant'
                    text TEXT NOT NULL,
                    intent TEXT,
                    entities TEXT, -- JSON structure
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()

    def get_or_create_session(self, session_id: str, language: str = "en") -> Dict[str, Any]:
        now_str = datetime.now().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                if row["language"] != language:
                    cursor.execute(
                        "UPDATE sessions SET language = ?, updated_at = ? WHERE session_id = ?",
                        (language, now_str, session_id)
                    )
                    conn.commit()
                
                # Fetch updated session
                cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                
                return {
                    "session_id": row["session_id"],
                    "language": row["language"],
                    "user_preferences": json.loads(row["user_preferences"]) if row["user_preferences"] else {},
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            else:
                prefs = {"created": now_str}
                cursor.execute(
                    "INSERT INTO sessions (session_id, language, user_preferences, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (session_id, language, json.dumps(prefs), now_str, now_str)
                )
                conn.commit()
                return {
                    "session_id": session_id,
                    "language": language,
                    "user_preferences": prefs,
                    "created_at": now_str,
                    "updated_at": now_str
                }

    def save_message(self, session_id: str, msg_id: str, sender: str, text: str, 
                     intent: Optional[str] = None, entities: Optional[Dict[str, Any]] = None, 
                     timestamp: Optional[str] = None):
        now_str = datetime.now().isoformat()
        if not timestamp:
            timestamp = datetime.now().strftime("%I:%M %p")
        if not msg_id:
            msg_id = f"msg-{datetime.now().timestamp()}"
        
        entities_str = json.dumps(entities) if entities else "{}"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            self.get_or_create_session(session_id)
            cursor.execute(
                "INSERT INTO messages (id, session_id, sender, text, intent, entities, timestamp, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (msg_id, session_id, sender, text, intent, entities_str, timestamp, now_str)
            )
            cursor.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now_str, session_id))
            conn.commit()

    def get_session_history(self, session_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            history = []
            for row in rows:
                history.append({
                    "id": row["id"],
                    "sender": row["sender"],
                    "text": row["text"],
                    "intent": row["intent"],
                    "entities": json.loads(row["entities"]) if row["entities"] else {},
                    "timestamp": row["timestamp"]
                })
            return history

    def get_last_entities_context(self, session_id: str) -> Dict[str, List[str]]:
        """Accumulates all entities extracted in the recent chat history to maintain context."""
        history = self.get_session_history(session_id, limit=6)
        context_entities = {
            "crops": [], "pests": [], "fertilizers": [],
            "soilTypes": [], "weather": [], "schemes": []
        }
        for msg in history:
            entities = msg.get("entities", {})
            for key in context_entities.keys():
                if key in entities and isinstance(entities[key], list):
                    for item in entities[key]:
                        if item not in context_entities[key]:
                            context_entities[key].append(item)
        return context_entities


class AgriculturalKnowledgeBase:
    """
    Data manager class for the agricultural knowledge base.
    Serves as the foundation for future LangChain document loading,
    vector embeddings, and RAG retrieval pipelines.
    """
    def __init__(self, data_path: Optional[str] = None):
        if not data_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.join(base_dir, "knowledge_base", "advisory_data.json")
        
        self.data_path = data_path
        self.data: Dict[str, Any] = {}
        self.load_documents()

    def load_documents(self):
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                print(f"Knowledge Base: Loaded documents from {self.data_path}")
            else:
                print(f"Knowledge Base Warning: Source {self.data_path} not found. Initializing empty.")
                self.data = {}
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            self.data = {}

    def retrieve_info(self, intent: str, entities: Dict[str, List[str]], query: str) -> str:
        """
        Scans loaded documents matching extracted entities and intents to compile
        expert-backed, structured advice context.
        """
        query_lower = query.lower()
        
        # 1. Pest Management / Plant Diseases
        if intent == "Pest Management" or "pest" in query_lower or "disease" in query_lower or "insect" in query_lower:
            pests = [p.lower() for p in entities.get("pests", [])]
            crops = [c.lower() for c in entities.get("crops", [])]
            
            # Look for matching pest in knowledge base
            for item in self.data.get("pest_management", []):
                p_name = item["pest_name"].lower()
                if p_name in pests or any(p_name in q for q in pests) or any(c in item["affected_crops"] for c in crops):
                    return (
                        f"According to ICAR guidelines for {item['pest_name']} control in crops ({', '.join(item['affected_crops'])}):\n"
                        f"- Symptoms: {item['symptoms']}\n"
                        f"- Organic Control: {item['organic_control']}\n"
                        f"- Chemical Control: {item['chemical_control']}"
                    )
            
            # Default Pest Advisory fallback
            return (
                "For general insect pest control, inspect leaf undersides for whiteflies or aphids. "
                "Apply Neem Seed Kernel Extract (NSKE 5%) or spray Neem Oil (5ml per liter of water mixed with 1ml liquid soap). "
                "For fungal disease symptoms (like spots or leaf rot), apply Carbendazim 50% WP at 2g/liter of water."
            )

        # 2. Soil Health / Fertilizers
        elif intent == "Soil Health" or "soil" in query_lower or "fertilizer" in query_lower or "manure" in query_lower:
            soil_types = [s.lower() for s in entities.get("soilTypes", [])]
            fertilizers = [f.lower() for f in entities.get("fertilizers", [])]
            
            # Match soil type details
            for item in self.data.get("soil_health", []):
                s_type = item["soil_type"].lower()
                if s_type in soil_types or any(s in query_lower for s in s_type.split()):
                    return (
                        f"Soil Management Profile ({item['soil_type'].capitalize()}):\n"
                        f"- Characteristics: {item['characteristics']}\n"
                        f"- Recommended Treatment: {item['recommended_treatment']}\n"
                        f"- Ideal Crops: {', '.join(item['suitable_crops']).capitalize()}"
                    )
            
            # Match fertilizer application guidelines
            for item in self.data.get("fertilizers", []):
                f_name = item["name"].lower()
                if f_name in fertilizers or f_name in query_lower:
                    return (
                        f"Fertilizer Advisory ({item['name'].upper()}):\n"
                        f"- Primary Nutrient: {item['nutrient']}\n"
                        f"- Timing of Application: {item['application_stage']}\n"
                        f"- Safety & Dosing Guidelines: {item['guidelines']}"
                    )

            return (
                "For optimal soil nutrition, apply 10-15 tonnes of well-decomposed Farmyard Manure (FYM) per hectare during land preparation. "
                "Get your soil tested at the local KVK to obtain a soil health card. "
                "Practice a balanced NPK fertilizer application ratio (typically 4:2:1 for cereals) and grow leguminous crops like cowpea or dhaincha."
            )

        # 3. Irrigation Methods
        elif intent == "Irrigation" or "water" in query_lower or "irrigation" in query_lower or "drip" in query_lower:
            for item in self.data.get("irrigation", []):
                i_type = item["type"].lower()
                if i_type in query_lower or any(w in query_lower for w in i_type.split()):
                    return (
                        f"Irrigation Guidelines ({item['type'].capitalize()}):\n"
                        f"- Best Suited For: {item['suitability']}\n"
                        f"- Advantages: {item['benefits']}\n"
                        f"- Operation Notes: {item['guidelines']}"
                    )
            return (
                "To optimize water usage, install Drip Irrigation for row crops (cotton, tomato, vegetables) or Sprinklers for cereals. "
                "Avoid waterlogging as it restricts oxygen to roots, and irrigate during the cool evening or early morning hours."
            )

        # 4. Government Schemes
        elif intent == "Government Schemes" or "scheme" in query_lower or "yojana" in query_lower or "subsidy" in query_lower:
            schemes = [s.lower() for s in entities.get("schemes", [])]
            for item in self.data.get("government_schemes", []):
                s_name = item["name"].lower()
                s_alias = item.get("alias", "").lower()
                if s_name in query_lower or s_alias in query_lower or any(s in schemes for s in [s_name, s_alias]):
                    premium_info = f"\n- Premium Structure: {item['premium']}" if "premium" in item else ""
                    return (
                        f"Government Scheme: {item['name'].upper()}\n"
                        f"- Benefits: {item['benefits']}\n"
                        f"- Eligibility Criteria: {item.get('eligibility', 'Open to all landholder farmers')}{premium_info}\n"
                        f"- Registration Portal & Details: {item['how_to_apply']}"
                    )
            return (
                "Under the PM-KISAN Yojana, eligible farmers receive ₹6,000 per year in three equal installments. "
                "For risk insurance, apply under Pradhan Mantri Fasal Bima Yojana (PMFBY). "
                "Register at your local Common Service Center (CSC) or contact the Agricultural Officer in your block."
            )

        # 5. Crop Advisory Sowing/Yield
        elif intent == "Crop Advisory" or "crop" in query_lower or "seed" in query_lower or "sow" in query_lower:
            crops = [c.lower() for c in entities.get("crops", [])]
            for item in self.data.get("crops", []):
                c_name = item["name"].lower()
                if c_name in crops or c_name in query_lower:
                    return (
                        f"Crop Advisory for {item['name'].capitalize()}:\n"
                        f"- Best Sowing Window: {item['sowing_season']}\n"
                        f"- Seed Rate: {item['seed_rate']}\n"
                        f"- Spacing Requirements: {item['spacing']}\n"
                        f"- Recommended High-Yield Varieties: {', '.join(item['varieties'])}\n"
                        f"- Cultivation Guide: {item['guidelines']}"
                    )
            return (
                "Before sowing, purchase certified high-yielding seed varieties. "
                "Treat seeds with Azotobacter or Trichoderma culture to prevent seedling blight. "
                "Sow in clean, weed-free soil with adequate basal fertilizer like NPK or DAP."
            )

        # 6. Weather-related advice
        elif intent == "Weather" or "weather" in query_lower or "rain" in query_lower or "temperature" in query_lower:
            return (
                "Monitor weather forecasts regularly. Avoid applying fertilizers, spraying insecticides, "
                "or irrigating fields if heavy rains are predicted within 24 hours. "
                "During high temperatures, increase irrigation frequency slightly to prevent moisture stress."
            )

        # 7. Fallback General Advice
        return (
            "To maximize crop yield, verify seed quality, conduct regular soil tests (every 2-3 years), "
            "implement crop rotation, monitor plant leaf health daily, and consult your nearest Krishi Vigyan Kendra (KVK)."
        )

# Initialize database singleton and KB singleton
db_instance = AdvisoryDB()
kb_instance = AgriculturalKnowledgeBase()
