import os
import re
from typing import Optional

from serpapi import GoogleSearch
from groq import Groq

# ---------------------------------
# Identity responses
# ---------------------------------
identity_responses = {
    "what is your name": "I'm EVO-AI, your virtual assistant.",
    "who are you": "I'm EVO-AI, an intelligent chatbot built to assist you.",
    "who made you": "I was created by B-Tech students of Ace Engineering College, Ghatkesar.",
    "tell me about yourself": "I'm EVO-AI, your smart conversational partner powered by AI."
}

# ---------------------------------
# Environment variables (Render injects these)
# ---------------------------------
SERP_API_KEY = os.getenv("SERP_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ---------------------------------
# Utility: clean output
# ---------------------------------
def clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text

# ---------------------------------
# Google (SERP API) fallback
# ---------------------------------
def search_google(query: str) -> Optional[str]:
    if not SERP_API_KEY:
        return None

    try:
        search = GoogleSearch({
            "q": query,
            "hl": "en",
            "gl": "us",
            "api_key": SERP_API_KEY
        })
        results = search.get_dict()

        if results.get("organic_results"):
            snippet = results["organic_results"][0].get("snippet")
            return clean_text(snippet) if snippet else None
    except Exception:
        return None

    return None

# ---------------------------------
# Groq (PRIMARY LLM)
# ---------------------------------
def ask_groq(prompt: str) -> Optional[str]:
    if not GROQ_API_KEY:
        return None

    try:
        client = Groq(api_key=GROQ_API_KEY)

        response = client.chat.completions.create(
            model="gemma-7b-it",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=512
        )

        return clean_text(response.choices[0].message.content)

    except Exception:
        return None

# ---------------------------------
# Main brain (NO DB, PURE LOGIC)
# ---------------------------------
def get_chat_response(user_input: str) -> str:
    if not user_input:
        return "❌ Empty message."

    query = user_input.lower().strip()

    # Identity shortcuts
    for key, value in identity_responses.items():
        if key in query:
            return value

    # 1️⃣ Groq (best)
    groq_answer = ask_groq(user_input)
    if groq_answer:
        return groq_answer

    # 2️⃣ Google (facts)
    google_answer = search_google(user_input)
    if google_answer:
        return google_answer

    # 3️⃣ Final fallback
    return "⚠️ I'm unable to answer that right now. Please try again later."
