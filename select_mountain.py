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
        hh = int(int(minutes)/60)
        mm = int(minutes) - hh*60
        return f"{hh:02d}:{mm:02d}"
    except:
        return minutes



def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--userRoute", default="user_route_db.py")
    parser.add_argument("-x", "--exclude")

    parser.add_argument("-r", "--minRouteTime", type=int)
    parser.add_argument("-R", "--maxRouteTime", type=int)

    parser.add_argument("-c", "--minClimbTime", type=int)
    parser.add_argument("-C", "--maxClimbTime", type=int)

    parser.add_argument("-d", "--distanceMin", type=float)
    parser.add_argument("-D", "--distanceMax", type=float)

    parser.add_argument("-e", "--elevationMin", type=int)
    parser.add_argument("-E", "--elevationMax", type=int)

    parser.add_argument("-a", "--altitudeMin", type=int)
    parser.add_argument("-A", "--altitudeMax", type=int)

    parser.add_argument("-nn", action="store_true")

    args = parser.parse_args()

    db = load_module("mountain_db.py")
    routes = load_module(os.path.expanduser(args.userRoute))

    exclude_uuid, exclude_name = load_excludes(os.path.expanduser(str(args.exclude)), db.MOUNTAINS)

    selected = []

    for mountain_uuid, mountain in db.MOUNTAINS.items():
        mountain_name = mountain["mountain_name"]

        if mountain_uuid in exclude_uuid:
            continue
        if mountain_name in exclude_name:
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
            if tid not in routes.USER_TOZANGUCHI:
                continue

            route_time = routes.USER_TOZANGUCHI[tid]["route_time_min"]

            if not filter_range(
                route_time,
                args.minRouteTime,
                args.maxRouteTime
            ):
                continue

            climb_time = th["climb_time_min"]

            if not filter_range(
                climb_time,
                args.minClimbTime,
                args.maxClimbTime
            ):
                continue

            distance = th["distance_min_km"]

            if not filter_range(
                distance,
                args.distanceMin,
                args.distanceMax
            ):
                continue

            elevation = th["elevation_gain_min"]

            if not filter_range(
                elevation,
                args.elevationMin,
                args.elevationMax
            ):
                continue

            trailheads.append(
                {
                    "route_time": route_time,
                    "data": th
                }
            )

        if trailheads:
            trailheads.sort(
                key=lambda x: (
                    x["data"]["climb_time_min"]+x["route_time"]
                )
            )

            best_route = trailheads[0]["route_time"]

            selected.append(
                {
                    "best_route": best_route,
                    "mountain": mountain,
                    "trailheads": trailheads
                }
            )

    selected.sort(key=lambda x: x["best_route"])

    if args.nn:
        names = []
        seen = set()

        for row in selected:
            name = row["mountain"]["mountain_name"]
            if name not in seen:
                names.append(name)
                seen.add(name)

        print(" ".join(names))
        return

    for row in selected:
        m = row["mountain"]

        flags = ",".join(m["flags"])

        print(
            f'{m["mountain_name"]}'
            f'({m["yomi"]})'
            f'({m["altitude"]}m)'
            f'({m["mountain_uuid"]}):'
            f'{flags}'
        )

        for th in row["trailheads"]:
            t = th["data"]
            route_time = th["route_time"]

            print(
                f'   {t["trailhead_name"]}'
                f'({t["latitude"]:.6f} {t["longitude"]:.6f})'
                f' : route={get_hhmm_from_min(route_time)}'
                f' climb={get_hhmm_from_min(t["climb_time_min"])}'
                f' dist={t["distance_min_km"]:.1f}km'
                f' gain={t["elevation_gain_min"]}m'
            )

        print()


if __name__ == "__main__":
    main()