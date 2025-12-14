import os
import requests
from flask import Flask, request, jsonify, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

# ---------------------------------
# Flask app
# ---------------------------------
app = Flask(__name__)

# ---------------------------------
# Session configuration (CRITICAL)
# ---------------------------------
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",   # REQUIRED for cross-site cookies
    SESSION_COOKIE_SECURE=True        # REQUIRED for HTTPS (Render/Vercel)
)

# ---------------------------------
# CORS (THE REAL FIX – NO WILDCARDS)
# ---------------------------------
ALLOWED_ORIGINS = {
    "https://evoai-chatbot-frontend.vercel.app",
    "https://evoai-chatbot-frontend-dyfew1sy0-pinumalla-sai-tejas-projects.vercel.app"
}

CORS(
    app,
    supports_credentials=True,
    origins=lambda origin: origin in ALLOWED_ORIGINS
)

# ---------------------------------
# MongoDB
# ---------------------------------
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not set")

client = MongoClient(MONGO_URI)
db = client["EVO_AI_DB"]

users = db["users"]
chat_history = db["chat_history"]

# ---------------------------------
# Optional AI backend
# ---------------------------------
AI_API_URL = os.getenv("AI_API_URL")

# ---------------------------------
# Health check
# ---------------------------------
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "EVO-AI backend"
    })

# ---------------------------------
# REGISTER (JSON)
# ---------------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    if users.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 409

    hashed = generate_password_hash(password)
    user = users.insert_one({
        "email": email,
        "password": hashed
    })

    session["user_id"] = str(user.inserted_id)
    return jsonify({"message": "Registered successfully"}), 201

# ---------------------------------
# LOGIN (JSON)
# ---------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = users.find_one({"email": email})

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = str(user["_id"])
    return jsonify({"message": "Login successful"}), 200

# ---------------------------------
# CHAT
# ---------------------------------
@app.route("/api/chat", methods=["POST"])
def api_chat():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    message = data.get("message", "").strip()
    if not message:
        return jsonify({"response": "❌ Empty message"})

    if AI_API_URL:
        try:
            r = requests.post(
                AI_API_URL,
                json={"message": message},
                timeout=60
            )
            response = r.json().get("response", "No AI response")
        except Exception:
            response = "⚠️ AI service unavailable"
    else:
        response = f"You said: {message}"

    chat_history.insert_one({
        "user_id": session["user_id"],
        "user_input": message,
        "bot_response": response
    })

    return jsonify({"response": response})

# ---------------------------------
# LOGOUT
# ---------------------------------
@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out"})

# ---------------------------------
# Global error handler (DEBUG FRIENDLY)
# ---------------------------------
@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "error": "Internal server error",
        "details": str(e)
    }), 500

# ---------------------------------
# Run (Render)
# ---------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
