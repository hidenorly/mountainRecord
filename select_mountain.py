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

import argparse
import importlib.util
import os


def load_module(path):
    spec = importlib.util.spec_from_file_location("mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load_resources(mountainDb, userRoute, exclude):
    db = load_module(mountainDb)
    routes = load_module(os.path.expanduser(userRoute))
    exclude_uuid, exclude_name = load_excludes(
        os.path.expanduser(str(exclude))
        if exclude else None,
        db.MOUNTAINS
    )
    return db, routes, exclude_uuid, exclude_name


def load_excludes(path, mountains):
    exclude_uuid = set()
    exclude_name = set()

    if not path:
        return exclude_uuid, exclude_name

    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue

                if s in mountains:
                    exclude_uuid.add(s)
                else:
                    exclude_name.add(s)
    except:
        pass

    return exclude_uuid, exclude_name


def filter_range(v, minv, maxv):
    if minv is not None and v < minv:
        return False
    if maxv is not None and v > maxv:
        return False
    return True


def get_hhmm_from_min(minutes):
    try:
        hh = int(minutes / 60)
        mm = int(minutes) - hh * 60
        return f"{hh:02d}:{mm:02d}"
    except:
        return str(minutes)

def get_min_from_hhmm(hhmm):
    if not hhmm:
        return None
    _hhmm = str(hhmm).split(":")
    try:
        hh = int(_hhmm[0])
        mm = int(_hhmm[1])
        return hh*60+mm
    except:
        return int(str(hhmm))

def is_mountain_excluded(mountain_uuid, mountain, exclude_uuid, exclude_name):
    if mountain_uuid in exclude_uuid:
        return True
    if mountain["mountain_name"] in exclude_name:
        return True
    return False


def filter_trailhead(th, routes, args):
    tid = th["trailhead_id"]

    if tid not in routes.USER_TOZANGUCHI:
        return None

    route_time = routes.USER_TOZANGUCHI[tid]["route_time_min"]

    if not filter_range(route_time, args.minRouteTime, args.maxRouteTime):
        return None

    climb_time = th["climb_time_min"]
    if not filter_range(climb_time, args.minClimbTime, args.maxClimbTime):
        return None

    distance = th["distance_min_km"]
    if not filter_range(distance, args.distanceMin, args.distanceMax):
        return None

    elevation = th["elevation_gain_min"]
    if not filter_range(elevation, args.elevationMin, args.elevationMax):
        return None

    return {
        "route_time": route_time,
        "data": th
    }


def collect_candidates(db, routes, args, exclude_uuid, exclude_name):
    selected = []

    for mountain_uuid, mountain in db.MOUNTAINS.items():
        if is_mountain_excluded(
            mountain_uuid,
            mountain,
            exclude_uuid,
            exclude_name
        ):
            continue

        altitude = mountain["altitude"]

        if not filter_range(
            altitude,
            args.altitudeMin,
            args.altitudeMax
        ):
            continue

        trailheads = []

        for tid, th in mountain["trailheads"].items():
            filtered = filter_trailhead(th, routes, args)
            if filtered:
                trailheads.append(filtered)

        if trailheads:
            trailheads.sort(
                key=lambda x: (
                    x["route_time"] +
                    x["data"]["climb_time_min"]
                )
            )

            selected.append(
                {
                    "best_route": trailheads[0]["route_time"],
                    "mountain": mountain,
                    "trailheads": trailheads
                }
            )

    return selected


def sort_candidates(selected):
    selected.sort(key=lambda x: x["best_route"])


def output_nn(selected):
    names = []
    seen = set()

    for row in selected:
        name = row["mountain"]["mountain_name"]
        if name not in seen:
            names.append(name)
            seen.add(name)

    print(" ".join(names))


def output_human(selected):
    for row in selected:
        m = row["mountain"]
        flags = ",".join(m["flags"])

        try:
            print(
                f'{m["mountain_name"]}'
                f'({m["yomi"]})'
                f'({m["altitude"]}m)'
                f'({m["mountain_uuid"]}):'
                f'{flags}'
            )
        except:
            pass

        for th in row["trailheads"]:
            t = th["data"]
            route_time = th["route_time"]

            try:
                print(
                    f'   {t["trailhead_name"]}'
                    f'({t["latitude"]:.6f} {t["longitude"]:.6f})'
                    f' : route={get_hhmm_from_min(route_time)}'
                    f' climb={get_hhmm_from_min(t["climb_time_min"])}'
                    f' dist={t["distance_min_km"]:.1f}km'
                    f' gain={t["elevation_gain_min"]}m'
                )
            except:
                print(f'ERROR:{t["trailhead_name"]}:{t}')
                pass

        print()


def output_results(selected, args):
    if args.nn:
        output_nn(selected)
    else:
        output_human(selected)



def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-m", "--mountainDb", default="mountain_db.py")
    parser.add_argument("-u", "--userRoute", default="user_route_db.py")
    parser.add_argument("-x", "--exclude", action='store', help='list of excluding mounntain')

    parser.add_argument("-r", "--minRouteTime", action='store', help='min driving time e.g. 60 or 1:00')
    parser.add_argument("-R", "--maxRouteTime", action='store', help='max driving time e.g. 90 or 1:30')

    parser.add_argument("-c", "--minClimbTime", action='store', help='min climb time e.g. 60 or 1:00')
    parser.add_argument("-C", "--maxClimbTime", action='store', help='max climb time e.g. 90 or 1:30')

    parser.add_argument("-d", "--distanceMin", type=float, action='store', help='min distance km')
    parser.add_argument("-D", "--distanceMax", type=float, action='store', help='max distance km')

    parser.add_argument("-e", "--elevationMin", type=int, action='store', help='min climb elevation [m]')
    parser.add_argument("-E", "--elevationMax", type=int, action='store', help='max climb elevation [m]')

    parser.add_argument("-a", "--altitudeMin", type=int, action='store', help='min mountain altitude [m]')
    parser.add_argument("-A", "--altitudeMax", type=int, action='store', help='max mountain altitude [m]')

    parser.add_argument("-nn", action="store_true")

    return parser.parse_args()


def main():
    args = parse_args()
    args.minRouteTime = get_min_from_hhmm(args.minRouteTime)
    args.maxRouteTime = get_min_from_hhmm(args.maxRouteTime)
    args.minClimbTime = get_min_from_hhmm(args.minClimbTime)
    args.maxClimbTime = get_min_from_hhmm(args.maxClimbTime)

    db, routes, exclude_uuid, exclude_name = load_resources(args.mountainDb, args.userRoute, args.exclude)

    selected = collect_candidates(
        db,
        routes,
        args,
        exclude_uuid,
        exclude_name
    )

    sort_candidates(selected)

    output_results(selected, args)


if __name__ == "__main__":
    main()