from flask import Flask, render_template, jsonify, request
import pymonetdb
import time

app = Flask(__name__)

TABLE_NAME = "maritime.wrecks"
DB_HOST = "localhost"
DB_PORT = 50000
DB_NAME = "shipwrecksdb"
DB_USER = "monetdb"
DB_PASS = "monetdb"


def get_db():
    return pymonetdb.connect(
        hostname=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        username=DB_USER,
        password=DB_PASS
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/overview")
def overview():
    conn = get_db()
    cur = conn.cursor()

    start = time.time()

    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    total = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE dangerous = TRUE")
    dangerous = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE visible = TRUE")
    visible = cur.fetchone()[0]

    cur.execute(f"SELECT AVG(depth) FROM {TABLE_NAME} WHERE depth IS NOT NULL")
    avg_depth = cur.fetchone()[0]

    end = time.time()

    cur.close()
    conn.close()

    return jsonify({
        "total_wrecks": total,
        "dangerous_wrecks": dangerous,
        "visible_wrecks": visible,
        "avg_depth": round(avg_depth, 2) if avg_depth is not None else 0,
        "query_time_ms": round((end - start) * 1000, 2)
    })


@app.route("/api/wrecks")
def get_wrecks():
    dangerous = request.args.get("dangerous")
    visible = request.args.get("visible")
    category = request.args.get("category")
    search = request.args.get("search", "").strip()
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    conn = get_db()
    cur = conn.cursor()

    query = f"""
        SELECT wreck_id, category_name, water_level, chart_name,
               latitude, longitude, depth, history, quasou, dangerous, visible
        FROM {TABLE_NAME}
        WHERE 1=1
    """
    params = []

    if dangerous in ["true", "false"]:
        query += " AND dangerous = %s"
        params.append(dangerous == "true")

    if visible in ["true", "false"]:
        query += " AND visible = %s"
        params.append(visible == "true")

    if category:
        query += " AND category_name = %s"
        params.append(category)

    if search:
        query += " AND (LOWER(history) LIKE %s OR LOWER(chart_name) LIKE %s OR CAST(wreck_id AS VARCHAR(20)) LIKE %s)"
        like_term = f"%{search.lower()}%"
        params.extend([like_term, like_term, f"%{search}%"])

    count_query = "SELECT COUNT(*) FROM (" + query + ") AS filtered_data"

    start = time.time()

    cur.execute(count_query, params)
    total_count = cur.fetchone()[0]

    query += " ORDER BY depth DESC NULLS LAST LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()

    end = time.time()

    data = []
    for row in rows:
        data.append({
            "wreck_id": row[0],
            "category_name": row[1],
            "water_level": row[2],
            "chart_name": row[3],
            "latitude": row[4],
            "longitude": row[5],
            "depth": row[6],
            "history": row[7],
            "quasou": row[8],
            "dangerous": row[9],
            "visible": row[10]
        })

    cur.close()
    conn.close()

    return jsonify({
        "records": data,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "query_time_ms": round((end - start) * 1000, 2)
    })


@app.route("/api/categories")
def categories():
    conn = get_db()
    cur = conn.cursor()

    start = time.time()

    cur.execute(f"""
        SELECT category_name, COUNT(*)
        FROM {TABLE_NAME}
        GROUP BY category_name
        ORDER BY COUNT(*) DESC
    """)
    rows = cur.fetchall()

    end = time.time()

    cur.close()
    conn.close()

    return jsonify({
        "data": [{"category": r[0], "count": r[1]} for r in rows],
        "query_time_ms": round((end - start) * 1000, 2)
    })


@app.route("/api/danger-status")
def danger_status():
    conn = get_db()
    cur = conn.cursor()

    start = time.time()

    cur.execute(f"""
        SELECT dangerous, COUNT(*)
        FROM {TABLE_NAME}
        GROUP BY dangerous
    """)
    rows = cur.fetchall()

    end = time.time()

    cur.close()
    conn.close()

    return jsonify({
        "data": [{"dangerous": str(r[0]), "count": r[1]} for r in rows],
        "query_time_ms": round((end - start) * 1000, 2)
    })


@app.route("/api/top-depths")
def top_depths():
    conn = get_db()
    cur = conn.cursor()

    start = time.time()

    cur.execute(f"""
        SELECT wreck_id, category_name, depth
        FROM {TABLE_NAME}
        WHERE depth IS NOT NULL
        ORDER BY depth DESC
        LIMIT 10
    """)
    rows = cur.fetchall()

    end = time.time()

    cur.close()
    conn.close()

    return jsonify({
        "data": [
            {"wreck_id": r[0], "category_name": r[1], "depth": r[2]}
            for r in rows
        ],
        "query_time_ms": round((end - start) * 1000, 2)
    })


@app.route("/api/categories-list")
def categories_list():
    conn = get_db()
    cur = conn.cursor()

    cur.execute(f"""
        SELECT DISTINCT category_name
        FROM {TABLE_NAME}
        WHERE category_name IS NOT NULL
        ORDER BY category_name
    """)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([r[0] for r in rows])


if __name__ == "__main__":
    app.run(debug=True)