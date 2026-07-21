#   Copyright 2026 hidenorly
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

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
import copy
import importlib.util
import pprint

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


def load_py_variable(filename, varname):
    if not filename or not os.path.exists(filename):
        return {}

    spec = importlib.util.spec_from_file_location("db", filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return copy.deepcopy(getattr(module, varname, {}))


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
        url_match = re.search(r"url\s+:\s+(.+)", block)

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
        url = url_match.group(1).strip()

        result.append({
            "mountain_uuid": generate_mountain_uuid(
                name_value, yomi, altitude, lat, lon
            ),
            "mountain_name": name_value,
            "yomi": yomi,
            "latitude": lat,
            "longitude": lon,
            "altitude": altitude,
            "url": url,
            "flags": categories
        })

    return result


def merge_mountain(dst, src):
    # URL
    if not dst.get("url") and src.get("url"):
        dst["url"] = src["url"]

    # flags
    flags = set(dst.get("flags", []))
    flags.update(src.get("flags", []))
    dst["flags"] = sorted(flags)

    # trailheads
    dst.setdefault("trailheads", {})

    for tid, trailhead in src.get("trailheads", {}).items():

        if tid not in dst["trailheads"]:
            dst["trailheads"][tid] = copy.deepcopy(trailhead)
        else:
            merge_trailhead(
                dst["trailheads"][tid],
                trailhead,
            )


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

def weighted_average(v1, n1, v2, n2):
    if v1 is None:
        return v2
    if v2 is None:
        return v1

    total = n1 + n2
    if total == 0:
        return None

    return (v1 * n1 + v2 * n2) / total


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

def merge_trailhead(dst, src):
    n1 = dst.get("sample_count", 0)
    n2 = src.get("sample_count", 0)

    dst["sample_count"] = n1 + n2

    # climb time
    dst["climb_time_min"] = min(
        dst["climb_time_min"],
        src["climb_time_min"],
    )

    dst["climb_time_max"] = max(
        dst["climb_time_max"],
        src["climb_time_max"],
    )

    dst["climb_time_median"] = int(round(
        weighted_average(
            dst["climb_time_median"],
            n1,
            src["climb_time_median"],
            n2,
        )
    ))

    # distance
    for key in (
        "distance_min_km",
        "distance_median_km",
        "distance_max_km",
    ):
        dst.setdefault(key, None)
        src.setdefault(key, None)

    if src["distance_min_km"] is not None:
        if dst["distance_min_km"] is None:
            dst["distance_min_km"] = src["distance_min_km"]
        else:
            dst["distance_min_km"] = min(
                dst["distance_min_km"],
                src["distance_min_km"],
            )

    if src["distance_max_km"] is not None:
        if dst["distance_max_km"] is None:
            dst["distance_max_km"] = src["distance_max_km"]
        else:
            dst["distance_max_km"] = max(
                dst["distance_max_km"],
                src["distance_max_km"],
            )

    dst["distance_median_km"] = weighted_average(
        dst["distance_median_km"],
        n1,
        src["distance_median_km"],
        n2,
    )

    # elevation
    for key in (
        "elevation_gain_min",
        "elevation_gain_median",
        "elevation_gain_max",
    ):
        dst.setdefault(key, None)
        src.setdefault(key, None)

    if src["elevation_gain_min"] is not None:
        if dst["elevation_gain_min"] is None:
            dst["elevation_gain_min"] = src["elevation_gain_min"]
        else:
            dst["elevation_gain_min"] = min(
                dst["elevation_gain_min"],
                src["elevation_gain_min"],
            )

    if src["elevation_gain_max"] is not None:
        if dst["elevation_gain_max"] is None:
            dst["elevation_gain_max"] = src["elevation_gain_max"]
        else:
            dst["elevation_gain_max"] = max(
                dst["elevation_gain_max"],
                src["elevation_gain_max"],
            )

    gain = weighted_average(
        dst["elevation_gain_median"],
        n1,
        src["elevation_gain_median"],
        n2,
    )

    if gain is not None:
        dst["elevation_gain_median"] = int(round(gain))

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


def merge_user_route(user_routes, trailhead_id, route_time, trailhead_name):
    if route_time is None:
        return

    if trailhead_id not in user_routes:
        user_routes[trailhead_id] = {
            "route_time_min": route_time,
            "trailhead_name": trailhead_name,
        }
        return

    user_routes[trailhead_id]["route_time_min"] = min(
        user_routes[trailhead_id]["route_time_min"],
        route_time,
    )


def merge_db(existing_db, new_db):
    result = copy.deepcopy(existing_db)

    for uuid, mountain in new_db.items():

        if uuid not in result:
            result[uuid] = copy.deepcopy(mountain)
        else:
            merge_mountain(
                result[uuid],
                mountain,
            )

    return result

def save_python_db(filename, varname, data):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"{varname} = ")
        pprint.pprint(
            data,
            stream=f,
            sort_dicts=False,
            width=120,
        )

def normalize(text):
    if text is None:
        return ""

    return (
        text.strip()
            .replace("ヶ", "")
            .replace("ケ", "")
            .replace("ガ", "")
            .replace("ヵ", "")
            .replace("（", "(")
            .replace("）", ")")
    )

def find_matching_info(key, infos):
    if len(infos) == 1:
        return infos[0]

    name, yomi, altitude = key

    name = normalize(name)
    yomi = normalize(yomi)

    best = None
    best_score = -1
    best_altitude_diff = 999999

    for info in infos:

        info_name = normalize(info["mountain_name"])
        info_yomi = normalize(info["yomi"])

        score = 0

        if info_name == name:
            score += 100

        if info_yomi == yomi:
            score += 80

        if (
            info_name.startswith(name)
            or name.startswith(info_name)
        ):
            score += 50

        if (
            info_yomi.startswith(yomi)
            or yomi.startswith(info_yomi)
        ):
            score += 30

        altitude_diff = abs(
            int(info["altitude"]) - altitude
        )

        if (
            score > best_score or
            (
                score == best_score and
                altitude_diff < best_altitude_diff
            )
        ):
            best = info
            best_score = score
            best_altitude_diff = altitude_diff

    if best_score <= 0:
        return None

    return best



def build_db(mountain_names, days, samples, user_out, existing_db=None, existing_user_routes=None):
    db = copy.deepcopy(existing_db or {})
    user_routes = copy.deepcopy(existing_user_routes or {})
    not_found = []
    no_recent_records = []
    info_mismatch = []

    is_wait_required = False

    for name in mountain_names:

        print("processing:", name)

        if is_wait_required:
            time.sleep(WAIT_SECONDS_PER_MOUNTAIN)
        is_wait_required = True

        infos = parse_mountain_info(name)
        if not infos:
            print(f"WARNING: mountain info not found: {name}")
            not_found.append(name)
            continue

        record_groups = parse_recent_records(name, days, samples)
        if not record_groups:
            print(f"WARNING: no recent records: {name}")
            no_recent_records.append(name)
            continue

        for key, urls in record_groups.items():
            info = find_matching_info(
                key,
                infos,
            )

            if info is None:
                print(
                    f"WARNING: cannot match mountain info: "
                    f"{key}"
                )
                continue

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

                trailhead_id = generate_trailhead_uuid(
                    lat,
                    lon,
                )

                trailhead_name = resolve_trailhead_name(
                    info["mountain_name"],
                    lat,
                    lon,
                )

                durations = [
                    x["duration_min"]
                    for x in rows
                ]

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

                    "climb_time_min": min(durations),
                    "climb_time_median": int(statistics.median(durations)),
                    "climb_time_max": max(durations),

                    "distance_min_km":
                        min(distances) if distances else None,
                    "distance_median_km":
                        statistics.median(distances)
                        if distances else None,
                    "distance_max_km":
                        max(distances) if distances else None,

                    "elevation_gain_min":
                        min(gains) if gains else None,
                    "elevation_gain_median":
                        int(statistics.median(gains))
                        if gains else None,
                    "elevation_gain_max":
                        max(gains) if gains else None,

                    "sample_count": len(rows),
                }

                # user_route_db
                if user_out:
                    route_time = get_route_time(lat, lon)

                    merge_user_route(
                        user_routes,
                        trailhead_id,
                        route_time,
                        trailhead_name,
                    )

            info["trailheads"] = trailheads

            uuid = info["mountain_uuid"]

            # merge into db
            if uuid not in db:
                db[uuid] = info
            else:
                merge_mountain(
                    db[uuid],
                    info,
                )

    return db, user_routes, {
        "not_found": not_found,
        "no_recent_records": no_recent_records,
        "info_mismatch": info_mismatch,
    }


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

    # load existing DB
    existing_db = load_py_variable(
        args.db_out,
        "MOUNTAINS",
    )

    existing_user_routes = load_py_variable(
        args.user_out,
        "USER_TOZANGUCHI",
    )

    # mountain names from csv
    all_names = load_mountains(args.csv)

    # skip already existing mountains
    existing_names = {
        mountain["mountain_name"]
        for mountain in existing_db.values()
    }

    target_names = [
        name
        for name in all_names
        if name not in existing_names
    ]

    print(
        f"{len(existing_names)} mountains already exist."
    )
    print(
        f"{len(target_names)} mountains will be fetched."
    )

    if not target_names:
        print("Nothing to do.")
        return

    # fetch & merge
    db, user_routes, report = build_db(
        target_names,
        args.days,
        args.samples,
        args.user_out,
        existing_db,
        existing_user_routes,
    )

    # save
    if args.db_out:
        save_python_db(
            args.db_out,
            "MOUNTAINS",
            db,
        )

    if args.user_out:
        save_python_db(
            args.user_out,
            "USER_TOZANGUCHI",
            user_routes,
        )

    print()
    print(
        f"Done. mountain_db={len(db)}, "
        f"user_route_db={len(user_routes)}"
    )
    if report["not_found"]:
        print()
        print("Mountain info not found:")
        for name in sorted(report["not_found"]):
            print("  ", name)

    if report["no_recent_records"]:
        print()
        print("No recent records:")
        for name in sorted(report["no_recent_records"]):
            print("  ", name)

    if report["info_mismatch"]:
        print()
        print("Info mismatch:")
        for item in report["info_mismatch"]:
            print(" ", item["mountain"])
            print("    record:", item["record"])


if __name__ == "__main__":
    main()