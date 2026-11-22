import os
import socket

import psycopg2
from flask import Flask

app = Flask(__name__)


def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


@app.route("/")
def home():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO visits DEFAULT VALUES")
        cur.execute("SELECT COUNT(*) FROM visits")
        total = cur.fetchone()[0]
    # Inside Kubernetes the hostname is the Pod name
    return f"<h1>Visits: {total}</h1><p>Served by pod: {socket.gethostname()}</p>"


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
