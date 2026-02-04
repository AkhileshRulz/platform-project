from flask import Flask
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
        return {"message": "DEPLOYMENT SUCCESSFUL 😈"}, 200
    except Exception as e:
        return f"DB connection failed: {e}"

@app.route("/health")
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
