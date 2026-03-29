import json
import pymonetdb

def extract_float(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        if "$numberDouble" in value:
            return float(value["$numberDouble"])
        if "$numberInt" in value:
            return float(value["$numberInt"])
    return None

conn = pymonetdb.connect(
    username="monetdb",
    password="monetdb",
    hostname="localhost",
    database="shipwrecksdb"
)

cursor = conn.cursor()
cursor.execute("SET SCHEMA maritime")

wreck_id = 1
inserted = 0
failed = 0

with open("shipwrecks.json", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        try:
            item = json.loads(line)

            feature = item.get("feature_type")
            water = item.get("watlev")
            chart = item.get("chart")
            history = item.get("history")
            quasou = item.get("quasou")

            lat = extract_float(item.get("latdec"))
            lon = extract_float(item.get("londec"))
            depth = extract_float(item.get("depth"))

            dangerous = False
            visible = False

            if feature:
                f_lower = feature.lower()
                dangerous = "dangerous" in f_lower
                visible = "visible" in f_lower

            if feature:
                try:
                    cursor.execute(
                        "INSERT INTO categories(category_name) VALUES (%s)",
                        (feature,)
                    )
                except:
                    conn.rollback()
                    cursor = conn.cursor()
                    cursor.execute("SET SCHEMA maritime")

            if water:
                try:
                    cursor.execute(
                        "INSERT INTO water_levels(water_level) VALUES (%s)",
                        (water,)
                    )
                except:
                    conn.rollback()
                    cursor = conn.cursor()
                    cursor.execute("SET SCHEMA maritime")

            if chart:
                try:
                    cursor.execute(
                        "INSERT INTO charts(chart_name) VALUES (%s)",
                        (chart,)
                    )
                except:
                    conn.rollback()
                    cursor = conn.cursor()
                    cursor.execute("SET SCHEMA maritime")

            cursor.execute("""
                INSERT INTO wrecks
                (wreck_id, category_name, water_level, chart_name, latitude, longitude, depth, history, quasou, dangerous, visible)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                wreck_id,
                feature,
                water,
                chart,
                lat,
                lon,
                depth,
                history,
                quasou,
                dangerous,
                visible
            ))

            conn.commit()
            inserted += 1
            wreck_id += 1

        except Exception as e:
            failed += 1
            print(f"Row {wreck_id} failed:", e)
            conn.rollback()
            cursor = conn.cursor()
            cursor.execute("SET SCHEMA maritime")
            wreck_id += 1

cursor.close()
conn.close()

print(f"Done. Inserted={inserted}, Failed={failed}")