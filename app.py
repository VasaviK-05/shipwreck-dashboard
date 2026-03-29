from flask import Flask, jsonify, render_template, request
import json
import math
from pathlib import Path

app = Flask(__name__)

DATA_FILE = Path(__file__).parent / "shipwrecks.json"


def unwrap_value(value):
    if isinstance(value, dict):
        if "$numberDouble" in value:
            try:
                return float(value["$numberDouble"])
            except (ValueError, TypeError):
                return None
        if "$oid" in value:
            return value["$oid"]
    return value


def to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def to_float(value):
    value = unwrap_value(value)
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def normalize_record(row, index):
    feature_type = str(row.get("feature_type") or "").strip()
    chart_name = str(row.get("chart") or "").strip()
    water_level = str(row.get("watlev") or "").strip()
    history = str(row.get("history") or "").strip()
    quasou = str(row.get("quasou") or "").strip()

    depth = to_float(row.get("depth"))
    latitude = to_float(row.get("latdec"))
    longitude = to_float(row.get("londec"))

    # Build consistent booleans for frontend
    dangerous = "danger" in feature_type.lower()
    visible = "visible" in feature_type.lower()

    # Prefer recid if present, otherwise use line index
    raw_wreck_id = row.get("recid")
    if raw_wreck_id in (None, ""):
        wreck_id = index + 1
    else:
        try:
            wreck_id = int(raw_wreck_id)
        except (ValueError, TypeError):
            wreck_id = index + 1

    return {
        "wreck_id": wreck_id,
        "category_name": feature_type if feature_type else "Unknown",
        "water_level": water_level if water_level else None,
        "chart_name": chart_name if chart_name else None,
        "latitude": latitude,
        "longitude": longitude,
        "depth": depth,
        "history": history if history else None,
        "quasou": quasou if quasou else None,
        "dangerous": dangerous,
        "visible": visible,
    }


def load_data():
    records = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for index, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                records.append(normalize_record(obj, index))
            except json.JSONDecodeError:
                continue
    return records


def matches_filters(row, args):
    search = args.get("search", "").strip().lower()
    category = args.get("category", "").strip()
    water_level = args.get("water_level", "").strip()
    chart_name = args.get("chart_name", "").strip()
    dangerous = args.get("dangerous", "").strip().lower()
    visible = args.get("visible", "").strip().lower()
    missing_depth = args.get("missing_depth", "").strip().lower()
    min_depth = args.get("min_depth", "").strip()
    max_depth = args.get("max_depth", "").strip()

    if search:
        haystack = " ".join([
            str(row.get("category_name") or ""),
            str(row.get("water_level") or ""),
            str(row.get("chart_name") or ""),
            str(row.get("history") or ""),
            str(row.get("quasou") or "")
        ]).lower()
        if search not in haystack:
            return False

    if category and (row.get("category_name") or "") != category:
        return False

    if water_level and (row.get("water_level") or "") != water_level:
        return False

    if chart_name and (row.get("chart_name") or "") != chart_name:
        return False

    if dangerous == "true" and not row.get("dangerous", False):
        return False

    if visible == "true" and not row.get("visible", False):
        return False

    depth = row.get("depth")

    if missing_depth == "true" and depth is not None:
        return False

    if min_depth:
        try:
            if depth is None or depth < float(min_depth):
                return False
        except ValueError:
            pass

    if max_depth:
        try:
            if depth is None or depth > float(max_depth):
                return False
        except ValueError:
            pass

    return True


def filtered_data(args):
    data = load_data()
    return [row for row in data if matches_filters(row, args)]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/filter-options")
def filter_options():
    data = load_data()

    categories = sorted({r["category_name"] for r in data if r.get("category_name")})
    water_levels = sorted({r["water_level"] for r in data if r.get("water_level")})
    charts = sorted({r["chart_name"] for r in data if r.get("chart_name")})

    return jsonify({
        "categories": categories,
        "water_levels": water_levels,
        "charts": charts
    })


@app.route("/api/stats")
def stats():
    data = filtered_data(request.args)

    total_wrecks = len(data)
    dangerous_wrecks = sum(1 for r in data if r.get("dangerous"))
    visible_wrecks = sum(1 for r in data if r.get("visible"))

    depths = [r["depth"] for r in data if r.get("depth") is not None]
    avg_depth = round(sum(depths) / len(depths), 2) if depths else None

    missing_depth_count = sum(1 for r in data if r.get("depth") is None)
    water_level_types = len({r["water_level"] for r in data if r.get("water_level")})

    return jsonify({
        "total_wrecks": total_wrecks,
        "dangerous_wrecks": dangerous_wrecks,
        "visible_wrecks": visible_wrecks,
        "avg_depth": avg_depth,
        "missing_depth_count": missing_depth_count,
        "water_level_types": water_level_types
    })


@app.route("/api/category-counts")
def category_counts():
    data = filtered_data(request.args)
    counts = {}

    for r in data:
        key = r.get("category_name") or "Unknown"
        counts[key] = counts.get(key, 0) + 1

    result = [
        {"category": k, "count": v}
        for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]
    return jsonify(result)


@app.route("/api/water-level-counts")
def water_level_counts():
    data = filtered_data(request.args)
    counts = {}

    for r in data:
        key = r.get("water_level") or "Unknown"
        counts[key] = counts.get(key, 0) + 1

    result = [
        {"water_level": k, "count": v}
        for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]
    return jsonify(result)


@app.route("/api/depth-bands")
def depth_bands():
    data = filtered_data(request.args)
    counts = {
        "Unknown": 0,
        "0-5 m": 0,
        "5-15 m": 0,
        "15-30 m": 0,
        "30+ m": 0
    }

    for r in data:
        depth = r.get("depth")
        if depth is None:
            counts["Unknown"] += 1
        elif depth < 5:
            counts["0-5 m"] += 1
        elif depth < 15:
            counts["5-15 m"] += 1
        elif depth < 30:
            counts["15-30 m"] += 1
        else:
            counts["30+ m"] += 1

    result = [
        {"band": k, "count": v}
        for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]
    return jsonify(result)


@app.route("/api/records")
def records():
    data = filtered_data(request.args)

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    try:
        per_page = int(request.args.get("per_page", 100))
    except ValueError:
        per_page = 100

    if per_page > 500:
        per_page = 500
    if page < 1:
        page = 1

    data = sorted(data, key=lambda r: (r.get("wreck_id") is None, r.get("wreck_id")))
    total_count = len(data)
    total_pages = math.ceil(total_count / per_page) if per_page else 1

    start = (page - 1) * per_page
    end = start + per_page
    records_page = data[start:end]

    return jsonify({
        "page": page,
        "per_page": per_page,
        "total_count": total_count,
        "total_pages": total_pages,
        "records": records_page
    })


@app.route("/api/record/<int:wreck_id>")
def record_detail(wreck_id):
    data = load_data()

    for row in data:
        if row.get("wreck_id") == wreck_id:
            return jsonify(row)

    return jsonify({"error": "Record not found"}), 404


@app.route("/api/data-quality")
def data_quality():
    data = filtered_data(request.args)

    missing_depth = sum(1 for r in data if r.get("depth") is None)
    missing_history = sum(1 for r in data if not (r.get("history") or "").strip())
    missing_quasou = sum(1 for r in data if not (r.get("quasou") or "").strip())
    missing_chart = sum(1 for r in data if not (r.get("chart_name") or "").strip())

    return jsonify({
        "missing_depth": missing_depth,
        "missing_history": missing_history,
        "missing_quasou": missing_quasou,
        "missing_chart": missing_chart
    })


if __name__ == "__main__":
    app.run(debug=True)