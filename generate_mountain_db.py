#!/usr/bin/env python3
import subprocess
import hashlib
import re
import math
import statistics
import argparse
from collections import defaultdict
import os
import time

TOZANGUCHI = os.path.expanduser("~/bin/get_tozanguchi.py")
ROUTE_TIME = os.path.expanduser("~/work/routeTime/get_route_time.py")
MOUNTAIN_INFO = os.path.expanduser("~/bin/get_mountain_info.py")
RECENT_RECORD = os.path.expanduser("~/bin/get_recent_record2.py")
DETAIL_RECORD = os.path.expanduser("~/bin/get_detail_record.py")

NEAR_DISTANCE_METER = 200
WAIT_SECONDS_PER_MOUNTAIN = 15
# TODO: add hinting info. for the trail heads
VERTICAL_ROUTE_KEYWORDS = [
    "縦走",
    "周回",
    "周遊",
    "テント泊",
    "小屋泊",
]

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True)


def distance_meter(lat1, lon1, lat2, lon2):
    dx = (lon1 - lon2) * 111000 * math.cos(math.radians(lat1))
    dy = (lat1 - lat2) * 111000
    return math.sqrt(dx * dx + dy * dy)


def generate_mountain_uuid(name, yomi, altitude, lat, lon):
    s = f"{name}|{yomi}|{altitude}|{lat:.5f}|{lon:.5f}"
    return hashlib.sha1(s.encode()).hexdigest()[:16]


def generate_trailhead_uuid(lat, lon):
    s = f"{lat:.5f}|{lon:.5f}"
    return hashlib.sha1(s.encode()).hexdigest()[:16]

def dms_to_decimal(deg, minute, sec):
    return deg + minute / 60.0 + sec / 3600.0

def parse_mountain_info(name):
    result = []
    out = ""
    try:
        out = run(f'python3 {MOUNTAIN_INFO} "{name}" -p yamareco')
    except:
        return result
    blocks = out.split("name       :")

    for block in blocks:
        if not block.strip():
            continue

        name_match = re.search(r"^\s*(.+)", block)
        yomi_match = re.search(r"yomi\s+:\s+(.+)", block)
        alt_match = re.search(r"altitude\s+:\s+([\d\.]+)", block)

        loc_match = re.search(
            r"北緯(\d+)度(\d+)分(\d+)秒,\s*東経(\d+)度(\d+)分(\d+)秒",
            block
        )

        categories = []
        cat_section = re.search(
            r"category\s+:(.*?)(?:description:|$)",
            block,
            re.S
        )

        if cat_section:
            categories = [
                x.strip()
                for x in cat_section.group(1).splitlines()
                if x.strip()
            ]

        if not all([name_match, yomi_match, alt_match, loc_match]):
            continue

        lat = (
            int(loc_match.group(1))
            + int(loc_match.group(2)) / 60
            + int(loc_match.group(3)) / 3600
        )

        lon = (
            int(loc_match.group(4))
            + int(loc_match.group(5)) / 60
            + int(loc_match.group(6)) / 3600
        )

        altitude = float(alt_match.group(1))
        name_value = name_match.group(1).strip()
        yomi = yomi_match.group(1).strip()

        result.append({
            "mountain_uuid": generate_mountain_uuid(
                name_value, yomi, altitude, lat, lon
            ),
            "mountain_name": name_value,
            "yomi": yomi,
            "latitude": lat,
            "longitude": lon,
            "altitude": altitude,
            "flags": categories
        })

    return result


def parse_recent_records(name, days, samples):
    out = ""
    grouped = defaultdict(list)
    try:
        out = run(f'python3 {RECENT_RECORD} "{name}" -p yamareco -d {days} -n {samples}')
    except:
        pass

    pattern = (
        r"name:(.*?), yomi:(.*?), altitude:(\d+)"
        r"\s*:\s*(https://\S+)"
    )

    for line in out.splitlines():
        m = re.search(pattern, line)
        if not m:
            continue

        key = (
            m.group(1).strip(),
            m.group(2).strip(),
            int(m.group(3))
        )

        grouped[key].append(m.group(4))

    return grouped

def safe_median(values):
    if not values:
        return None
    return statistics.median(values)


def is_vertical_route(title):
    if not title:
        return False

    return any(
        keyword in title
        for keyword in VERTICAL_ROUTE_KEYWORDS
    )

def parse_detail(url):
    out = ""
    try:
        out = run(f'python3 {DETAIL_RECORD} "{url}"')
    except:
        return None

    duration = re.search(r'duration\s*:\s*(\d+):(\d+)', out)
    distance = re.search(r'distance\s*:\s*([\d\.]+)km', out)
    gain = re.search(r'elevation_gained\s*:\s*([\d,]+)m', out)
    access = re.search(
        r'access_lat_lon\s*:\s*([\d\.]+)\s+([\d\.]+)', out
    )
    title = re.search(r'title\s*:\s*(.+)', out)

    if not duration or not access:
        return None

    duration_min = (
        int(duration.group(1)) * 60 +
        int(duration.group(2))
    )

    return {
        "duration_min": duration_min,
        "distance_km":
            float(distance.group(1)) if distance else None,
        "elevation_gain":
            int(gain.group(1).replace(",", "")) if gain else None,
        "lat": float(access.group(1)),
        "lon": float(access.group(2)),
        "title": title.group(1).strip() if title else None
    }

def cluster_trailheads(records):
    clusters = []

    for rec in records:
        merged = False

        for cluster in clusters:
            center = cluster["center"]
            d = distance_meter(
                rec["lat"], rec["lon"],
                center["lat"], center["lon"]
            )

            if d <= NEAR_DISTANCE_METER:
                cluster["records"].append(rec)

                cluster["center"]["lat"] = statistics.mean(
                    [x["lat"] for x in cluster["records"]]
                )
                cluster["center"]["lon"] = statistics.mean(
                    [x["lon"] for x in cluster["records"]]
                )
                merged = True
                break

        if not merged:
            clusters.append({
                "center": {"lat": rec["lat"], "lon": rec["lon"]},
                "records": [rec]
            })

    return clusters


def parse_tozanguchi(mountain_name):
    try:
        out = run(f'python3 {TOZANGUCHI} "{mountain_name}"')
    except:
        return []

    result = []
    current_name = None

    for line in out.splitlines():
        m = re.match(r"^\s*(.+?)\s*:\s*https://", line)
        if m:
            current_name = m.group(1).strip()

        loc = re.search(r"緯度経度\s*:\s*([\d\.]+)\s+([\d\.]+)", line)

        if loc and current_name:
            result.append({
                "name": current_name,
                "lat": float(loc.group(1)),
                "lon": float(loc.group(2))
            })

    return result


def resolve_trailhead_name(mountain_name, lat, lon):
    candidates = parse_tozanguchi(mountain_name)

    best = None
    best_dist = 999999

    for c in candidates:
        d = distance_meter(lat, lon, c["lat"], c["lon"])
        if d < best_dist:
            best = c
            best_dist = d

    if best and best_dist <= NEAR_DISTANCE_METER:
        return best["name"]

    return f"{mountain_name}_登山口駐車場"


def get_route_time(lat, lon):
    try:
        out = run(f'python3 {ROUTE_TIME} {lat} {lon}')
    except:
        return None

    m = re.search(r"Estimated duration:\s*(\d+)\s*時間\s*(\d+)\s*分", out)
    if not m:
        return None

    return int(m.group(1)) * 60 + int(m.group(2))


def build_db(mountain_names, days, samples):
    db = {}
    user_routes = {}
    is_wait_required = False

    for name in mountain_names:
        print("processing:", name)
        if is_wait_required:
            time.sleep(WAIT_SECONDS_PER_MOUNTAIN)
            is_wait_required = True

        infos = parse_mountain_info(name)
        record_groups = parse_recent_records(name, days, samples)

        info_map = {
            (x["mountain_name"], x["yomi"], int(x["altitude"])): x
            for x in infos
        }

        for key, urls in record_groups.items():
            if key not in info_map:
                continue

            info = info_map[key]

            records = []
            for url in urls:
                detail = parse_detail(url)
                if detail:
                    records.append(detail)

            if not records:
                continue

            clusters = cluster_trailheads(records)
            trailheads = {}

            for cluster in clusters:
                rows = cluster["records"]
                lat = cluster["center"]["lat"]
                lon = cluster["center"]["lon"]

                trailhead_id = generate_trailhead_uuid(lat, lon)
                trailhead_name = resolve_trailhead_name(
                    info["mountain_name"], lat, lon
                )

                durations = [x["duration_min"] for x in rows]

                distances = [
                    x["distance_km"]
                    for x in rows
                    if x["distance_km"] is not None
                ]

                gains = [
                    x["elevation_gain"]
                    for x in rows
                    if x["elevation_gain"] is not None
                ]

                trailheads[trailhead_id] = {
                    "trailhead_id": trailhead_id,
                    "trailhead_name": trailhead_name,
                    "latitude": lat,
                    "longitude": lon,

                    # climb time stats
                    "climb_time_min": min(durations),
                    "climb_time_median": int(statistics.median(durations)),
                    "climb_time_max": max(durations),

                    # distance stats
                    "distance_min_km":
                        min(distances) if distances else None,
                    "distance_median_km":
                        statistics.median(distances) if distances else None,
                    "distance_max_km":
                        max(distances) if distances else None,

                    # elevation stats
                    "elevation_gain_min":
                        min(gains) if gains else None,
                    "elevation_gain_median":
                        int(statistics.median(gains)) if gains else None,
                    "elevation_gain_max":
                        max(gains) if gains else None,

                    "sample_count": len(rows)
                }

                route_time = get_route_time(lat, lon)
                if route_time:
                    user_routes[trailhead_id] = {
                        "route_time_min": route_time,
                        "trailhead_name": trailhead_name
                    }

            info["trailheads"] = trailheads
            db[info["mountain_uuid"]] = info

    return db, user_routes


def load_mountains(files):
    result = []
    seen = set()

    for file in files:
        with open(file) as f:
            for line in f:
                name = line.strip()
                if name and name not in seen:
                    seen.add(name)
                    result.append(name)

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", nargs="+")
    parser.add_argument("--db-out", default="mountain_db.py")
    parser.add_argument("--user-out", default="user_route_db.py")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--samples", type=int, default=5)
    args = parser.parse_args()

    names = load_mountains(args.csv)
    db, user_routes = build_db(names, args.days, args.samples)

    with open(args.db_out, "w", encoding="utf-8") as f:
        f.write("MOUNTAINS = ")
        f.write(repr(db))

    with open(args.user_out, "w", encoding="utf-8") as f:
        f.write("USER_TOZANGUCHI = ")
        f.write(repr(user_routes))


if __name__ == "__main__":
    main()