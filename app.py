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

# Railway MySQL fix
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# Model (MATCHES DB EXACTLY)
# -----------------------------
class AIInsight(db.Model):
    __tablename__ = "ai_insights"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    ai_json = db.Column(db.JSON)

# -----------------------------
# Health check
# -----------------------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "ai-insights-api"
    }

# -----------------------------
# Insert endpoint
# -----------------------------
@app.post("/api/ai-insights")
def insert_ai_insight():
    data = request.get_json(force=True)

    record = AIInsight(
        ai_json=data   # 👈 store EXACT JSON as-is
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
# Local dev entry
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
