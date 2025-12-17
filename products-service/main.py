from flask import Flask, request, jsonify
import psycopg2
import socket
import redis
import json
from psycopg2 import errors

app = Flask(__name__)
redis_client = redis.StrictRedis(host="redis", port=6379, db=0, decode_responses=True)

def get_conn():
    return psycopg2.connect(
        host="db",
        database="usersdb",
        user="eya",            # corrige si besoin pour la prod
        password="eyaalimi123"
    )

def to_dict_product(row):
    if row:
        return {"id": row[0], "name": row[1], "price": float(row[2]), "category": row[3]}
    return None

@app.route("/whoami")
def whoami():
    return jsonify({"hostname": socket.gethostname()})

@app.get("/products")
def get_products():
    # Optimisation : pagination & tri
    limit = min(int(request.args.get("limit", 20)), 100)  # max 100 par page
    offset = int(request.args.get("offset", 0))
    order = request.args.get("order", "DESC").upper()
    if order not in ["ASC", "DESC"]: order = "DESC"
    cached_key = f"products_all_{limit}_{offset}_{order}"
    cached_products = redis_client.get(cached_key)
    if cached_products:
        return jsonify(json.loads(cached_products)), 200
    conn = get_conn()
    cur = conn.cursor()
    # Projection ciblée + tri + pagination
    cur.execute(f"""
        SELECT p.id, p.name, p.price, c.name AS category
        FROM products p
        LEFT JOIN category c ON p.category_id = c.id
        ORDER BY p.id {order}
        LIMIT %s OFFSET %s
    """, (limit, offset))
    rows = cur.fetchall()
    conn.close()
    res = [to_dict_product(row) for row in rows]
    redis_client.setex(cached_key, 60, json.dumps(res))
    return jsonify(res)

@app.get("/products/<id>")
def get_product(id):
    conn = get_conn()
    cur = conn.cursor()
    # Projection ciblée
    cur.execute("""
        SELECT p.id, p.name, p.price, c.name AS category
        FROM products p
        LEFT JOIN category c ON p.category_id = c.id
        WHERE p.id=%s
    """, (id,))
    row = cur.fetchone()
    conn.close()
    prod = to_dict_product(row)
    if prod:
        return jsonify(prod)
    else:
        return jsonify({"error": "Product not found"}), 404

@app.post("/products")
def add_product():
    data = request.json
    required_fields = ["name", "price", "category_id"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO products(name, price, category_id) VALUES (%s,%s,%s) RETURNING id, name, price, category_id",
            (data["name"], data["price"], data["category_id"])
        )
        conn.commit()
        prod = cur.fetchone()
        cur.execute("""
            SELECT p.id, p.name, p.price, c.name AS category
            FROM products p
            LEFT JOIN category c ON p.category_id = c.id
            WHERE p.id=%s
        """, (prod[0],))
        row = cur.fetchone()
    except errors.UniqueViolation:
        conn.rollback()
        return jsonify({"error": "Product Already Exists"}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
    # Invalide le cache sur tout
    for k in redis_client.scan_iter("products_all*"):
        redis_client.delete(k)
    return jsonify(to_dict_product(row)), 201

@app.delete("/products/<id>")
def delete_product(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    for k in redis_client.scan_iter("products_all*"):
        redis_client.delete(k)
    return jsonify({"message": "Product deleted"})

@app.get("/categories")
def get_categories():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, description FROM category ORDER BY id ASC")
    rows = [dict(zip([desc[0] for desc in cur.description], row)) for row in cur.fetchall()]
    conn.close()
    return jsonify(rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000)