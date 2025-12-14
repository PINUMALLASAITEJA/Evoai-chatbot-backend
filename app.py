import os
import requests
from flask import Flask, request, jsonify, session, make_response
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------
# Flask app
# ---------------------------------
app = Flask(__name__)

# ---------------------------------
# Secrets & session
# ---------------------------------
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

# ---------------------------------
# Allowed frontend origins
# ---------------------------------
ALLOWED_ORIGINS = [
    "https://evoai-chatbot-frontend.vercel.app",
    "https://evoai-chatbot-frontend-dyfew1sy0-pinumalla-sai-tejas-projects.vercel.app"
]

# ---------------------------------
# MongoDB
# ---------------------------------
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["EVO_AI_DB"]

users = db["users"]
chat_history = db["chat_history"]

# ---------------------------------
# AI backend (optional)
# ---------------------------------
AI_API_URL = os.getenv("AI_API_URL")

# ---------------------------------
# CORS HEADERS (MANUAL & RELIABLE)
# ---------------------------------
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"

    return response


# ---------------------------------
# OPTIONS handler (CRITICAL)
# ---------------------------------
@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return make_response("", 204)


# ---------------------------------
# Health
# ---------------------------------
@app.route("/")
def health():
    return jsonify({"status": "ok"})


# ---------------------------------
# REGISTER
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
    user = users.insert_one({"email": email, "password": hashed})

    session["user_id"] = str(user.inserted_id)
    return jsonify({"message": "Registered successfully"}), 201


# ---------------------------------
# LOGIN
# ---------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

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
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"response": "❌ Empty message"})

    if AI_API_URL:
        r = requests.post(AI_API_URL, json={"message": message}, timeout=60)
        response = r.json().get("response", "No AI response")
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
# Run (Render)
# ---------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
