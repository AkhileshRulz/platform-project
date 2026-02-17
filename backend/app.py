from flask import Flask, request, jsonify, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_httpauth import HTTPBasicAuth
import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)

logger = logging.getLogger(__name__)

class Config:
    DB_HOST = os.environ.get("DB_HOST")
    DB_NAME = os.environ.get("POSTGRES_DB")
    DB_USER = os.environ.get("POSTGRES_USER")
    DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD")

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="redis://redis:6379",
    default_limits=["100 per minute"]
)

auth = HTTPBasicAuth()

USERS = {
    os.environ.get("API_USER"): os.environ.get("API_PASS")
}

@auth.verify_password
def verify(username, password):
    if not username or not password:
        return False
    return USERS.get(username) == password

@app.before_request
def start_timer():
    g.start_time = time.time()

REQUEST_COUNT = Counter(
    "app_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "app_request_latency_seconds",
    "Request latency",
    ["endpoint"]
)

@app.after_request
def log_request(response):
    duration = time.time() - g.start_time

    REQUEST_COUNT.labels(
        request.method, request.path, response.status_code
    ).inc()

    REQUEST_LATENCY.labels(request.path).observe(duration)

    logger.info(
        f"{request.method} {request.path} {response.status_code} {round(duration*1000)}ms"
    )
    return response

@app.route("/")
def home():
    return "Backend is running!"

db_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=5,
    host=Config.DB_HOST,
    database=Config.DB_NAME,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    connect_timeout=1
)

def get_db_connection():
    return db_pool.getconn()

def insert_note(content):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO notes (content) VALUES (%s) RETURNING id;", (content,))
    note_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    db_pool.putconn(conn)
    return note_id

def fetch_notes():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, content, created_at FROM notes ORDER BY created_at DESC;")
    rows = cur.fetchall()
    cur.close()
    db_pool.putconn(conn)
    return rows

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

@app.route("/db")
def db_test():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        return {"message": "AUTO DEPLOY WORKED"}, 200
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return "Database error", 500

@app.route("/notes", methods=["POST"])
@auth.login_required
@limiter.limit("10 per minute")
def add_note():
    try:
        data = request.get_json()

        if not data or "content" not in data:
            return jsonify({"error": "Content is required"}), 400

        content = data["content"].strip()

        if not content:
            return jsonify({"error": "Content cannot be empty"}), 400

        note_id = insert_note(content)
        logger.info(f"Creating note with content length={len(content)}")
        return jsonify({"id": note_id, "content": content}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/notes", methods=["GET"])
def get_notes():
    rows = fetch_notes()

    notes = [{"id": r[0], "content": r[1], "created_at": r[2].isoformat()} for r in rows]
    return jsonify(notes), 200

@app.route("/live")
def live():
    return {"status": "alive"}, 200

@app.route("/ready")
def ready():
    try:
        conn = get_db_connection()
        db_pool.putconn(conn)
        return {"status": "ready"}, 200
    except Exception as e:
        logger.error(f"Readiness failed: {e}")
        return {"status": "not ready"}, 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
