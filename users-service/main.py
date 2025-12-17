from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import errors
import socket
import redis
import json
from dotenv import load_dotenv
import os
from marshmallow import Schema, fields, ValidationError
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

app = Flask(__name__)
load_dotenv()
CORS(app, origins=["https://tonsite.com"], methods=["GET", "POST"])

security_logger = logging.getLogger("security")
handler = logging.FileHandler("security.log")
security_logger.addHandler(handler)
security_logger.setLevel(logging.INFO)

limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)

redis_client = redis.StrictRedis(host="redis", port=6379, db=0, decode_responses=True)

DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")

def get_conn():
    return psycopg2.connect(
        host="db",
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

class UserSchema(Schema):
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    role_id = fields.Int(required=False, allow_none=True)

REQUEST_COUNT = Counter(
    'users_service_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'users_service_request_latency_seconds',
    'Latency of HTTP requests in seconds',
    ['method', 'endpoint']
)

@app.before_request
def log_security():
    ip = request.remote_addr
    endpoint = request.endpoint
    method = request.method
    user_agent = request.headers.get('User-Agent')
    security_logger.info(f"{ip} {method} {endpoint} UA:{user_agent}")
    request.start_time = time.time()

@app.after_request
def after_request(response):
    latency = time.time() - getattr(request, 'start_time', time.time())
    REQUEST_LATENCY.labels(request.method, request.path).observe(latency)
    REQUEST_COUNT.labels(
        request.method,
        request.path,
        str(response.status_code)
    ).inc()
    return response

@app.route("/whoami")
def whoami():
    return jsonify({"hostname": socket.gethostname()})

@app.get("/users")
def get_users():
    # Pagination : ?limit=10&offset=0
    # Par défaut limite à 20 résultats, offset à 0
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = int(request.args.get("offset", 0))
    cached_users = redis_client.get(f"users_all_{limit}_{offset}")
    if cached_users:
        return jsonify(json.loads(cached_users)), 200

    conn = get_conn()
    cur = conn.cursor()
    # Optimisation : projection ciblée + tri + pagination
    cur.execute("""
        SELECT u.id, u.name, u.email, r.name AS role
        FROM users u
        LEFT JOIN role r ON u.role_id = r.id
        ORDER BY u.id DESC
        LIMIT %s OFFSET %s
    """, (limit, offset))
    rows = [dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()]
    conn.close()
    redis_client.setex(f"users_all_{limit}_{offset}", 60, json.dumps(rows))
    return jsonify(rows)

@app.get("/users/<id>")
def get_user(id):
    conn = get_conn()
    cur = conn.cursor()
    # Optimisation : projection ciblée
    cur.execute("""
        SELECT u.id, u.name, u.email, r.name AS role
        FROM users u
        LEFT JOIN role r ON u.role_id = r.id
        WHERE u.id = %s
    """, (id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({"message": "User not found"}), 404
    return jsonify(dict(zip([desc[0] for desc in cur.description], row)))

@app.post("/users")
@limiter.limit("5 per minute")
def add_user():
    schema = UserSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return err.messages, 400

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users(name,email,role_id) VALUES (%s,%s,%s) RETURNING id, name, email, role_id",
            (data["name"], data["email"], data.get("role_id"))
        )
        conn.commit()
        user = cur.fetchone()
    except errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    finally:
        conn.close()
    redis_client.delete("users_all_20_0")  # Invalide le cache par défaut
    # Projection ciblée pour le retour
    if user:
        user_id = user[0]
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.name, u.email, r.name AS role
            FROM users u
            LEFT JOIN role r ON u.role_id = r.id
            WHERE u.id = %s
        """, (user_id,))
        row = cur.fetchone()
        conn.close()
        return jsonify(dict(zip([desc[0] for desc in cur.description], row))), 201
    return jsonify({"error": "User creation failed"}), 400

@app.put("/users/<id>")
def update_user(id):
    schema = UserSchema(partial=True)
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return err.messages, 400

    fields_to_update = []
    params = []
    for key in ("name", "email", "role_id"):
        if key in data:
            fields_to_update.append(f"{key}=%s")
            params.append(data[key])
    if not fields_to_update:
        return jsonify({"error": "No data to update"}), 400
    params.append(id)

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            f"UPDATE users SET {', '.join(fields_to_update)} WHERE id=%s RETURNING id, name, email, role_id",
            params
        )
        conn.commit()
        updated_user = cur.fetchone()
    except errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    finally:
        conn.close()
    redis_client.delete("users_all_20_0")
    if updated_user:
        user_id = updated_user[0]
        conn = get_conn()
        cur = conn.cursor()
        # Projection ciblée pour le retour
        cur.execute("""
            SELECT u.id, u.name, u.email, r.name AS role
            FROM users u
            LEFT JOIN role r ON u.role_id = r.id
            WHERE u.id = %s
        """, (user_id,))
        row = cur.fetchone()
        conn.close()
        return jsonify(dict(zip([desc[0] for desc in cur.description], row)))
    else:
        return jsonify({"message": "User not found"}), 404

@app.delete("/users/<id>")
def delete_user(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    redis_client.delete("users_all_20_0")
    return jsonify({"message": "User deleted"})

@app.get("/roles")
def get_roles():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM role ORDER BY id ASC")
    rows = [dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)