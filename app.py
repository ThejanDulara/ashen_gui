import os
import requests as http_requests
from dotenv import load_dotenv
load_dotenv()

import werkzeug
werkzeug.__version__ = "3.1.3"

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from openai import OpenAI

app = Flask(__name__)
CORS(app)

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")

# -----------------------------
# DATABASE (UNCHANGED)
# -----------------------------
DATABASE_URL = "mysql://root:vQwgQKOMCDmBNdmSmkQSHykfNPPYGBpK@shortline.proxy.rlwy.net:41051/railway"
DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# OPENAI SETUP (NEW)
# -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set")

client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# MODELS (EXISTING + NEW)
# -----------------------------
class AIInsight(db.Model):
    __tablename__ = "ai_insights"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    ai_json = db.Column(db.Text)   # ← raw storage


class Business360Raw(db.Model):
    __tablename__ = "media_overview"

    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.JSON, nullable=True)

# -----------------------------
# HEALTH (UNCHANGED)

# -----------------------------
# CHAT MEMORY (SIMPLE)
# -----------------------------
CHAT_HISTORY = []
MAX_HISTORY = 5

# -----------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}

LIVEAVATAR_API = 'https://api.liveavatar.com'

# ── Create session token (server-side, API key never sent to browser) ──
@app.post("/api/liveavatar-token")
def liveavatar_token():
    if not HEYGEN_API_KEY:
        return jsonify({"error": "HEYGEN_API_KEY not configured"}), 500

    try:
        body = request.get_json(silent=True) or {}

        avatar_id = body.get("avatar_id") or "65ef6e2a-0c30-4e34-9e38-59839390ad4e"
        voice_id = body.get("voice_id") or "c2527536-6d1f-4412-a643-53a3497dada9"

        resp = http_requests.post(
            f"{LIVEAVATAR_API}/v1/sessions/token",
            headers={
                "x-api-key": HEYGEN_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "mode": "FULL",
                "avatar_id": avatar_id,
                "avatar_persona": {
                    "voice_id": voice_id
                }
            },
            timeout=15,
        )

        data = resp.json()

        if resp.status_code != 200:
            return jsonify({
                "error": data.get("detail") or data.get("message", "LiveAvatar error"),
                "code": resp.status_code,
                "full_response": data  # 👈 useful debug
            }), resp.status_code

        token = data.get("data", {}).get("session_token")

        if not token:
            token = data.get("token") or data.get("session_token")

        return jsonify({"token": token})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Start session (can be called from frontend with the token) ──────────
@app.post("/api/liveavatar-start")
def liveavatar_start():
    body = request.get_json() or {}
    token = body.get("token")
    if not token:
        return jsonify({"error": "token required"}), 400
    try:
        resp = http_requests.post(
            f"{LIVEAVATAR_API}/v1/sessions/start",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={},
            timeout=20,
        )
        data = resp.json()
        if resp.status_code != 200:
            return jsonify({"error": data.get("detail") or data.get("message", "LiveAvatar start error"), "code": resp.status_code}), resp.status_code
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Stop session ────────────────────────────────────────────────────────
@app.post("/api/liveavatar-stop")
def liveavatar_stop():
    body = request.get_json() or {}
    session_id = body.get("session_id")
    if not session_id or not HEYGEN_API_KEY:
        return jsonify({"ok": False}), 400
    try:
        http_requests.post(
            f"{LIVEAVATAR_API}/v1/sessions/stop",
            headers={"x-api-key": HEYGEN_API_KEY, "Content-Type": "application/json"},
            json={"session_id": session_id},
            timeout=10,
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------
# INSERT AI INSIGHTS (UNCHANGED)
# -----------------------------
@app.post("/api/ai-insights")
def insert_ai_insight():

    # 🔥 Get raw body (never fails)
    raw_body = request.get_data(as_text=True)

    if not raw_body:
        return jsonify({
            "ok": False,
            "error": "Empty request body"
        }), 400

    record = AIInsight(
        ai_json=raw_body   # ← store EXACTLY what arrived
    )

    try:
        db.session.add(record)
        db.session.commit()
        return jsonify({
            "ok": True,
            "id": record.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


@app.get("/api/ai-insights/latest")
def get_latest_ai_insight():
    row = (
        db.session.query(AIInsight)
        .order_by(AIInsight.id.desc())
        .first()
    )

    if not row:
        return jsonify({"ok": False, "error": "No data"}), 404

    return jsonify({
        "ok": True,
        "data": row.ai_json
    })


@app.post("/api/media-overview")
def insert_media_overview():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({
            "ok": False,
            "error": "Invalid or missing JSON payload"
        }), 400

    record = Business360Raw(data=data)
    try:
        db.session.add(record)
        db.session.commit()
        return jsonify({
            "ok": True,
            "id": record.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500


# -----------------------------
# HELPERS (NEW)
# -----------------------------
def get_latest_business_summary():
    row = (
        db.session.query(Business360Raw)
        .order_by(Business360Raw.id.desc())
        .first()
    )
    return row.data if row else []


def get_recent_ai_insights(limit=5):
    rows = (
        db.session.query(AIInsight)
        .order_by(AIInsight.id.desc())
        .limit(limit)
        .all()
    )
    return [r.ai_json for r in rows]


def ask_openai(prompt):
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a senior business analyst. Explain trends and reasons clearly."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return response.choices[0].message.content

# -----------------------------
# CHATBOT ENDPOINT (NEW)
# -----------------------------
@app.post("/api/chat")
def chat():

    body = request.get_json()
    question = body.get("question")

    if not question:
        return jsonify({"ok": False, "error": "Question required"}), 400

    # Save question to memory
    CHAT_HISTORY.append({"role": "user", "content": question})

    if len(CHAT_HISTORY) > MAX_HISTORY * 2:
        CHAT_HISTORY[:] = CHAT_HISTORY[-MAX_HISTORY * 2:]

    summary_data = get_latest_business_summary()
    insights_history = get_recent_ai_insights()

    prompt = f"""
BUSINESS SUMMARY DATA (JSON):
{summary_data}

PREVIOUS AI INSIGHTS:
{insights_history}

CONVERSATION HISTORY:
{CHAT_HISTORY}

USER QUESTION:
{question}

Answer clearly in business language.
Explain WHY changes happened.
"""

    try:
        answer = ask_openai(prompt)

        # Save assistant reply
        CHAT_HISTORY.append({"role": "assistant", "content": answer})

        return jsonify({
            "ok": True,
            "answer": answer
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# -----------------------------
# LOCAL DEV (UNCHANGED)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

