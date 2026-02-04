from flask import Flask, request, jsonify
import os
import psycopg2

app = Flask(__name__)

@app.route("/")
def home():
    return "Backend is running!"

@app.route("/db")
def db_test():
    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST"),
            database=os.environ.get("POSTGRES_DB"),
            user=os.environ.get("POSTGRES_USER"),
            password=os.environ.get("POSTGRES_PASSWORD")
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        return {"message": "AUTO DEPLOY WORKED"}, 200
    except Exception as e:
        return f"DB connection failed: {e}"

@app.route("/notes", methods=["POST"])
def add_note():
    data = request.get_json()
    content = data.get("content")

    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD")
    )
    cur = conn.cursor()
    cur.execute("INSERT INTO notes (content) VALUES (%s) RETURNING id;", (content,))
    note_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"id": note_id, "content": content}), 201

@app.route("/notes", methods=["GET"])
def get_notes():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD")
    )
    cur = conn.cursor()
    cur.execute("SELECT id, content, created_at FROM notes ORDER BY created_at DESC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    notes = [{"id": r[0], "content": r[1], "created_at": r[2].isoformat()} for r in rows]
    return jsonify(notes), 200

@app.route("/health")
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
