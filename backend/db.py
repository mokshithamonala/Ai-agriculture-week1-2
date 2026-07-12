import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kisan_sahayak.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database tables for session management and chat logs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Sessions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            selected_language TEXT DEFAULT 'en',
            user_preferences TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Messages Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            sender TEXT CHECK(sender IN ('user', 'assistant')),
            text TEXT NOT NULL,
            translated_text TEXT,
            intent TEXT,
            entities TEXT DEFAULT '{}',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"Database: Initialized successfully at {DB_PATH}")

def save_session(session_id: str, language: str, preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Saves or updates a user session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    pref_str = json.dumps(preferences or {})
    now = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO sessions (session_id, selected_language, user_preferences, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            selected_language = excluded.selected_language,
            user_preferences = excluded.user_preferences,
            updated_at = excluded.updated_at
    """, (session_id, language, pref_str, now, now))
    
    conn.commit()
    conn.close()
    return {"session_id": session_id, "language": language, "preferences": preferences or {}}

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves session details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "session_id": row["session_id"],
            "selected_language": row["selected_language"],
            "user_preferences": json.loads(row["user_preferences"] or "{}"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    return None

def add_message(session_id: str, sender: str, text: str, translated_text: Optional[str] = None, intent: Optional[str] = None, entities: Optional[Dict[str, Any]] = None) -> int:
    """Logs a chat message to database history."""
    # Ensure session exists first
    session = get_session(session_id)
    if not session:
        save_session(session_id, "en")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    entity_str = json.dumps(entities or {})
    now = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO messages (session_id, sender, text, translated_text, intent, entities, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, sender, text, translated_text, intent, entity_str, now))
    
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return msg_id

def get_conversation_history(session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieves the history of messages for a session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM messages 
        WHERE session_id = ? 
        ORDER BY timestamp ASC 
        LIMIT ?
    """, (session_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "id": row["id"],
            "sender": row["sender"],
            "text": row["text"],
            "translated_text": row["translated_text"],
            "intent": row["intent"],
            "entities": json.loads(row["entities"] or "{}"),
            "timestamp": row["timestamp"]
        })
    return history

# Initialize on import
init_db()
