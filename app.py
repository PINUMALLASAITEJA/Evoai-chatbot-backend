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
# Session config (MANDATORY for cross-site)
# ---------------------------------
app.secret_key = os.getenv("FLASK_SECRET_KEY")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
)

# ---------------------------------
# CORS (FIXED & SAFE)
# ---------------------------------
CORS(
    app,
    supports_credentials=True,
    resources={
        r"/api/*": {
            "origins": [
                "https://evoai-chatbot-frontend.vercel.app",
                "https://*.vercel.app"
            ]
        }
    }
)

# ---------------------------------
# MongoDB
# ---------------------------------
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["EVO_AI_DB"]

users = db["users"]
chat_history = db["chat_history"]

# ---------------------------------
# Health check
# ---------------------------------
@app.route("/")
def health():
    return jsonify({"status": "ok"})

# ---------------------------------
# REGISTER
# ---------------------------------
@app.route("/api/register", methods=["POST", "OPTIONS"])
def api_register():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json()
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
@app.route("/api/login", methods=["POST", "OPTIONS"])
def api_login():
    if request.method == "OPTIONS":
        return "", 204

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

# ---------------------------------
# CHAT
# ---------------------------------
@app.route("/api/chat", methods=["POST", "OPTIONS"])
def api_chat():
    if request.method == "OPTIONS":
        return "", 204

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

# ---------------------------------
# LOGOUT
# ---------------------------------
@app.route("/api/logout", methods=["POST", "OPTIONS"])
def api_logout():
    if request.method == "OPTIONS":
        return "", 204

    session.clear()
    return jsonify({"message": "Logged out"})

# ---------------------------------
# Run (Render)
# ---------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
