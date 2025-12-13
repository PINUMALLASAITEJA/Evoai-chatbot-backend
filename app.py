import os
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from pymongo import MongoClient
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from bson.objectid import ObjectId

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv(dotenv_path="config/.env")

# -------------------------------
# Initialize Flask app
# -------------------------------
app = Flask(__name__)


CORS(
    app,
    supports_credentials=True,
    origins=[
        "https://evoai-chatbot-frontend.vercel.app",
        "https://evoai-chatbot-frontend-a3lychp50-pinumalla-sai-tejas-projects.vercel.app"
    ]
)


app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

# -------------------------------
# MongoDB setup
# -------------------------------
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = "EVO_AI_DB"

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[MONGO_DB]
users = db["users"]
chat_history = db["chat_history"]

# -------------------------------
# Render AI API
# -------------------------------
AI_API_URL = os.getenv("AI_API_URL")  # Render URL

# -------------------------------
# Routes
# -------------------------------

@app.route("/")
def home():
    return jsonify({
        "status": "OK",
        "message": "EVO-AI backend is running"
    })


# -------------------------------
# Login
# -------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = users.find_one({"email": email})
        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            flash("Login successful", "success")
            return redirect(url_for("chatbot"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")

# -------------------------------
# Register
# -------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if users.find_one({"email": email}):
            flash("Email already registered.", "warning")
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(password)
        new_user = users.insert_one({
            "email": email,
            "password": hashed_password
        })

        session["user_id"] = str(new_user.inserted_id)
        flash("Registration successful!", "success")
        return redirect(url_for("chatbot"))

    return render_template("register.html")

# -------------------------------
# Chat UI
# -------------------------------
@app.route("/chatbot")
def chatbot():
    if "user_id" not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for("login"))
    return render_template("chat.html")

# -------------------------------
# Chat API (CALLS RENDER)
# -------------------------------
@app.route("/get_response", methods=["POST"])
def get_response():
    if "user_id" not in session:
        return jsonify({"response": "Unauthorized"}), 401

    user_input = request.json.get("message", "").strip()
    user_id = session.get("user_id")

    if not user_input:
        return jsonify({"response": "❌ Empty input."})

    try:
        # Call Render AI backend
        r = requests.post(
            AI_API_URL,
            json={
                "message": user_input,
                "user_id": user_id
            },
            timeout=60
        )

        r.raise_for_status()
        response = r.json().get("response", "⚠️ No response from AI")

        # Save history
        chat_history.insert_one({
            "user_id": user_id,
            "user_input": user_input,
            "bot_response": response
        })

        return jsonify({"response": response})

    except Exception as e:
        print("AI ERROR:", e)
        return jsonify({"response": "⚠️ AI service unavailable."})

# -------------------------------
# Logout
# -------------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
