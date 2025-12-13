import os
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from serpapi import GoogleSearch
from groq import Groq

# -------------------------------
# Identity responses
# -------------------------------
identity_responses = {
    "what is your name": "I'm EVO-AI, your virtual assistant.",
    "who are you": "I'm EVO-AI, an intelligent chatbot built to assist you.",
    "who made you": "I was created by B-tech students of Ace Engineering College, Ghatkesar.",
    "tell me about yourself": "I'm EVO-AI, your smart conversational partner powered by AI technologies."
}

# -------------------------------
# Environment variables (Render will inject these)
# -------------------------------
SERP_API_KEY = os.getenv("SERP_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")

# -------------------------------
# Torch device
# -------------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -------------------------------
# Load GPT-Neo model (lightweight)
# -------------------------------
def load_model():
    model_name = "EleutherAI/gpt-neo-125M"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
    model.eval()
    return tokenizer, model

tokenizer, model = load_model()

# -------------------------------
# Utility: clean output
# -------------------------------
def clean_text(text: str) -> str:
    text = text.strip()
    if "..." in text:
        parts = re.split(r'(?<=[.!?])\s+', text)
        text = " ".join(p for p in parts if not p.endswith("..."))
    return text

# -------------------------------
# Google (SERP API) fallback
# -------------------------------
def search_google(query: str) -> str | None:
    if not SERP_API_KEY:
        return None

    params = {
        "q": query,
        "hl": "en",
        "gl": "us",
        "api_key": SERP_API_KEY
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        if results.get("organic_results"):
            snippet = results["organic_results"][0].get("snippet")
            return clean_text(snippet) if snippet else None
    except Exception:
        pass

    return None

# -------------------------------
# Groq (LLM API)
# -------------------------------
def ask_groq(prompt: str) -> str | None:
    if not GROK_API_KEY:
        return None

    try:
        client = Groq(api_key=GROK_API_KEY)
        response = client.chat.completions.create(
            model="gemma-7b-it",
            messages=[{"role": "user", "content": prompt}]
        )
        return clean_text(response.choices[0].message.content)
    except Exception:
        return None

# -------------------------------
# GPT-Neo fallback
# -------------------------------
def generate_gpt_neo(prompt: str) -> str | None:
    try:
        input_ids = tokenizer.encode(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            output = model.generate(
                input_ids,
                max_new_tokens=200,
                temperature=0.9,
                top_k=50,
                top_p=0.95,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )

        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        reply = decoded.replace(prompt, "").strip()
        return clean_text(reply) if reply else None
    except Exception:
        return None

# -------------------------------
# Main brain (NO DATABASE)
# -------------------------------
def get_chat_response(user_input: str) -> str:
    query = user_input.lower().strip()

    # Identity shortcuts
    for key, value in identity_responses.items():
        if key in query:
            return value

    # Groq (best quality)
    groq_answer = ask_groq(user_input)
    if groq_answer:
        return groq_answer

    # Google factual fallback
    google_answer = search_google(user_input)
    if google_answer:
        return google_answer

    # Local GPT-Neo fallback
    neo_answer = generate_gpt_neo(user_input)
    if neo_answer:
        return neo_answer

    return "❌ Sorry, I couldn’t find a reliable answer right now."
