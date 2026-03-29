from flask import Flask, jsonify, render_template, request
import pymonetdb

app = Flask(__name__)

def get_conn():
    return pymonetdb.connect(
        username="monetdb",
        password="monetdb",
        hostname="localhost",
        database="shipwrecksdb"
    )

def apply_filters(base_query, args):
    filters = []
    params = []

    search = args.get("search", "").strip()
    category = args.get("category", "").strip()
    water_level = args.get("water_level", "").strip()
    chart_name = args.get("chart_name", "").strip()
    dangerous = args.get("dangerous", "").strip()
    visible = args.get("visible", "").strip()
    missing_depth = args.get("missing_depth", "").strip()
    min_depth = args.get("min_depth", "").strip()
    max_depth = args.get("max_depth", "").strip()

    if search:
        filters.append("""
            (
                LOWER(COALESCE(category_name, '')) LIKE %s OR
                LOWER(COALESCE(water_level, '')) LIKE %s OR
                LOWER(COALESCE(chart_name, '')) LIKE %s OR
                LOWER(COALESCE(history, '')) LIKE %s OR
                LOWER(COALESCE(quasou, '')) LIKE %s
            )
        """)
        value = f"%{search.lower()}%"
        params.extend([value, value, value, value, value])

    if category:
        filters.append("category_name = %s")
        params.append(category)

    if water_level:
        filters.append("water_level = %s")
        params.append(water_level)

    if chart_name:
        filters.append("chart_name = %s")
        params.append(chart_name)

    if dangerous == "true":
        filters.append("dangerous = TRUE")

    if visible == "true":
        filters.append("visible = TRUE")

    if missing_depth == "true":
        filters.append("depth IS NULL")

    if min_depth:
        filters.append("depth >= %s")
        params.append(float(min_depth))

    if max_depth:
        filters.append("depth <= %s")
        params.append(float(max_depth))

    if filters:
        base_query += " WHERE " + " AND ".join(filters)

    return base_query, params


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/filter-options")
def filter_options():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET SCHEMA maritime")

    cur.execute("SELECT DISTINCT category_name FROM wrecks WHERE category_name IS NOT NULL ORDER BY category_name")
    categories = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT DISTINCT water_level FROM wrecks WHERE water_level IS NOT NULL ORDER BY water_level")
    water_levels = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT DISTINCT chart_name FROM wrecks WHERE chart_name IS NOT NULL ORDER BY chart_name")
    charts = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify({
        "categories": categories,
        "water_levels": water_levels,
        "charts": charts
    })


@app.route("/api/stats")
def stats():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET SCHEMA maritime")

    stats_base = "SELECT COUNT(*) FROM wrecks"
    stats_base, stats_params = apply_filters(stats_base, request.args)
    cur.execute(stats_base, stats_params)
    total_wrecks = cur.fetchone()[0]

    dangerous_query = "SELECT COUNT(*) FROM wrecks"
    dangerous_query, dangerous_params = apply_filters(dangerous_query, request.args)
    if " WHERE " in dangerous_query:
        dangerous_query += " AND dangerous = TRUE"
    else:
        dangerous_query += " WHERE dangerous = TRUE"
    cur.execute(dangerous_query, dangerous_params)
    dangerous_wrecks = cur.fetchone()[0]

    visible_query = "SELECT COUNT(*) FROM wrecks"
    visible_query, visible_params = apply_filters(visible_query, request.args)
    if " WHERE " in visible_query:
        visible_query += " AND visible = TRUE"
    else:
        visible_query += " WHERE visible = TRUE"
    cur.execute(visible_query, visible_params)
    visible_wrecks = cur.fetchone()[0]

    avg_query = "SELECT AVG(depth) FROM wrecks"
    avg_query, avg_params = apply_filters(avg_query, request.args)
    if " WHERE " in avg_query:
        avg_query += " AND depth IS NOT NULL"
    else:
        avg_query += " WHERE depth IS NOT NULL"
    cur.execute(avg_query, avg_params)
    avg_depth = cur.fetchone()[0]

    missing_depth_query = "SELECT COUNT(*) FROM wrecks"
    missing_depth_query, missing_depth_params = apply_filters(missing_depth_query, request.args)
    if " WHERE " in missing_depth_query:
        missing_depth_query += " AND depth IS NULL"
    else:
        missing_depth_query += " WHERE depth IS NULL"
    cur.execute(missing_depth_query, missing_depth_params)
    missing_depth_count = cur.fetchone()[0]

    water_types_query = "SELECT COUNT(DISTINCT water_level) FROM wrecks"
    water_types_query, water_types_params = apply_filters(water_types_query, request.args)
    cur.execute(water_types_query, water_types_params)
    water_level_types = cur.fetchone()[0]

    cur.close()
    conn.close()

    return jsonify({
        "total_wrecks": total_wrecks,
        "dangerous_wrecks": dangerous_wrecks,
        "visible_wrecks": visible_wrecks,
        "avg_depth": round(avg_depth, 2) if avg_depth is not None else None,
        "missing_depth_count": missing_depth_count,
        "water_level_types": water_level_types
    })


@app.route("/api/category-counts")
def category_counts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET SCHEMA maritime")

    query = """
        SELECT category_name, COUNT(*)
        FROM wrecks
    """
    query, params = apply_filters(query, request.args)
    query += " GROUP BY category_name ORDER BY COUNT(*) DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([{"category": r[0], "count": r[1]} for r in rows])


@app.route("/api/water-level-counts")
def water_level_counts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET SCHEMA maritime")

    query = """
        SELECT water_level, COUNT(*)
        FROM wrecks
    """
    query, params = apply_filters(query, request.args)
    query += " GROUP BY water_level ORDER BY COUNT(*) DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([{"water_level": r[0], "count": r[1]} for r in rows])


@app.route("/api/depth-bands")
def depth_bands():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET SCHEMA maritime")

    inner_query = """
        SELECT
            CASE
                WHEN depth IS NULL THEN 'Unknown'
                WHEN depth < 5 THEN '0-5 m'
                WHEN depth < 15 THEN '5-15 m'
                WHEN depth < 30 THEN '15-30 m'
                ELSE '30+ m'
            END AS band
        FROM wrecks
    """
    inner_query, params = apply_filters(inner_query, request.args)

    outer_query = f"""
        SELECT band, COUNT(*) AS total
        FROM ({inner_query}) AS depth_data
        GROUP BY band
        ORDER BY total DESC
    """

    cur.execute(outer_query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([{"band": r[0], "count": r[1]} for r in rows])


@app.route("/api/records")
def records():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET SCHEMA maritime")

    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 100))
    if per_page > 500:
        per_page = 500

    offset = (page - 1) * per_page

    base_query = """
        SELECT wreck_id, category_name, water_level, chart_name,
               latitude, longitude, depth, history, quasou, dangerous, visible
        FROM wrecks
    """

    count_query = "SELECT COUNT(*) FROM wrecks"

    filtered_query, params = apply_filters(base_query, request.args)
    filtered_count_query, count_params = apply_filters(count_query, request.args)

    filtered_query += " ORDER BY wreck_id LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    cur.execute(filtered_count_query, count_params)
    total_count = cur.fetchone()[0]

    cur.execute(filtered_query, params)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": (total_count + per_page - 1) // per_page,
        "records": [
            {
                "wreck_id": r[0],
                "category_name": r[1],
                "water_level": r[2],
                "chart_name": r[3],
                "latitude": r[4],
                "longitude": r[5],
                "depth": r[6],
                "history": r[7],
                "quasou": r[8],
                "dangerous": r[9],
                "visible": r[10]
            }
            for r in rows
        ]
    })


@app.route("/api/record/<int:wreck_id>")
def record_detail(wreck_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET SCHEMA maritime")
    cur.execute("""
        SELECT wreck_id, category_name, water_level, chart_name,
               latitude, longitude, depth, history, quasou, dangerous, visible
        FROM wrecks
        WHERE wreck_id = %s
    """, (wreck_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Record not found"}), 404

    return jsonify({
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


@app.route("/api/data-quality")
def data_quality():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET SCHEMA maritime")

    base = "FROM wrecks"
    base, params = apply_filters(base, request.args)

    cur.execute(f"SELECT COUNT(*) {base} AND depth IS NULL" if " WHERE " in base else f"SELECT COUNT(*) {base} WHERE depth IS NULL", params)
    missing_depth = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) {base} AND (history IS NULL OR history = '')" if " WHERE " in base else f"SELECT COUNT(*) {base} WHERE (history IS NULL OR history = '')", params)
    missing_history = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) {base} AND (quasou IS NULL OR quasou = '')" if " WHERE " in base else f"SELECT COUNT(*) {base} WHERE (quasou IS NULL OR quasou = '')", params)
    missing_quasou = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) {base} AND (chart_name IS NULL OR chart_name = '')" if " WHERE " in base else f"SELECT COUNT(*) {base} WHERE (chart_name IS NULL OR chart_name = '')", params)
    missing_chart = cur.fetchone()[0]

    cur.close()
    conn.close()

    return jsonify({
        "missing_depth": missing_depth,
        "missing_history": missing_history,
        "missing_quasou": missing_quasou,
        "missing_chart": missing_chart
    })


if __name__ == "__main__":
    app.run(debug=True)