import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# -----------------------------
# App setup
# -----------------------------
app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# Model
# -----------------------------
class AIInsight(db.Model):
    __tablename__ = "ai_insights"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    ai_json = db.Column(db.Text)   # ← raw storage

# -----------------------------
# Health
# -----------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}

# -----------------------------
# Insert endpoint (ULTRA SAFE)
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

# -----------------------------
# Local dev
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
