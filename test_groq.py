import os
import sys
import json
import asyncio
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# Load environment
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env.local"))

from main import chat_endpoint, ChatRequest, health_check

async def run_tests():
    output = {}
    
    # 1. Test Health
    health = await health_check()
    output["health"] = health
    
    # 2. Test English Chat Response
    req = ChatRequest(
        message="Which fertilizer should I use for rice in sandy soil?",
        language="en",
        sessionId="test-session-1",
        mode="text"
    )
    res = await chat_endpoint(req)
    output["english_chat"] = {
        "intent": res.get("intent"),
        "entities": res.get("entities"),
        "response": res.get("response")
    }
    
    # 3. Test Translation and Multilingual Flow
    req_hi = ChatRequest(
        message="टमाटर की फसल में कौन सा खाद डालना चाहिए?",
        language="hi",
        sessionId="test-session-1",
        mode="text"
    )
    res_hi = await chat_endpoint(req_hi)
    output["hindi_chat"] = {
        "original_query": res_hi.get("original_query"),
        "translated_query": res_hi.get("translated_query"),
        "response": res_hi.get("response")
    }
    
    # Write to file in UTF-8
    with open("test_output.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("Test run successfully completed. Outputs written to test_output.json")

if __name__ == "__main__":
    asyncio.run(run_tests())
