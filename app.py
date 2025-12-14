import os
import requests
from flask import Flask, request, jsonify, session
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash

# ===============================
# Flask app
# ===============================
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret")

# ===============================
# Session cookies (cross-site)
# ===============================
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

# ===============================
# CORS — HARD FIX (Render safe)
# ===============================
FRONTEND_ORIGINS = [
    "https://evoai-chatbot-frontend.vercel.app",
]

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    # Allow main frontend + ALL Vercel preview URLs
    if origin and (
        origin in FRONTEND_ORIGINS
        or origin.endswith(".vercel.app")
    ):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"

    return response

# Handle preflight
@app.route("/api/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return "", 204

# ===============================
# MongoDB
# ===============================
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["EVO_AI_DB"]

users = db["users"]
chat_history = db["chat_history"]

# ===============================
# Health check
# ===============================
@app.route("/")
def health():
    return jsonify({"status": "ok"})

# ===============================
# REGISTER
# ===============================
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json()

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

# ===============================
# LOGIN
# ===============================
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = users.find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = str(user["_id"])
    return jsonify({"message": "Login successful"}), 200

# ===============================
# CHAT
# ===============================
@app.route("/api/chat", methods=["POST"])
def api_chat():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"response": "❌ Empty message"})

    response = f"You said: {message}"

    chat_history.insert_one({
        "user_id": session["user_id"],
        "user_input": message,
        "bot_response": response
    })

    return jsonify({"response": response})

# ===============================
# LOGOUT
# ===============================
@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out"})

# ===============================
# RUN (Render)
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
