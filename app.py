import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import json
from flask import request, jsonify

# -----------------------------
# App setup
# -----------------------------
app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Railway MySQL fix (optional but safe)
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(50))
    year_month = db.Column(db.String(20))
    insights = db.Column(db.JSON)
    reasons = db.Column(db.JSON)
    risks = db.Column(db.JSON)
    recommendations = db.Column(db.JSON)
    raw_response = db.Column(db.Text)

# -----------------------------
# Health check (Railway uses this)
# -----------------------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ai-insights-api",
    }

# -----------------------------
# Insert endpoint
# -----------------------------
@app.post("/api/ai-insights")
def insert_ai_insight():
    data = request.get_json(force=True)

    record = AIInsight(
        source=data.get("source"),
        yearMonth=data.get("yearMonth"),   # <-- match DB column

        insights=json.dumps(data.get("insights", [])),
        reasons=json.dumps(data.get("reasons", [])),
        risks=json.dumps(data.get("risks", [])),
        recommendations=json.dumps(data.get("recommendations", [])),

        raw_response=data.get("raw_response"),
    )

    try:
        db.session.add(record)
        db.session.commit()
        return jsonify({"ok": True, "id": record.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

# -----------------------------
# Local dev entry (Railway ignores this)
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
