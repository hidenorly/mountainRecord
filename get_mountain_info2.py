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

from select_mountain import *

import argparse
import time
from mountainRecordUtil import ExecUtil


def collect_candidates(db, routes, exclude_uuid, exclude_name, altitudeMin, altitudeMax, minRouteTime, maxRouteTime, minClimbTime, maxClimbTime, distanceMin, distanceMax, elevationMin, elevationMax, category, mountains):
    selected = []

    categories = None
    if category:
        categories = category.split(",")

    for mountain_uuid, mountain in db.MOUNTAINS.items():
        if mountain_uuid in mountains or mountain["mountain_name"] in mountains or mountain["yomi"] in mountains:
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
	            altitudeMin,
	            altitudeMax
	        ):
	            continue

	        if not is_target_category(mountain["flags"], categories):
	            continue

	        trailheads = []

	        for tid, th in mountain["trailheads"].items():
	            filtered = filter_trailhead(
	                th, routes,
	                minRouteTime, maxRouteTime,
	                minClimbTime, maxClimbTime,
	                distanceMin, distanceMax,
	                elevationMin, elevationMax
	            )
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
                f'{m["url"]}'
            )
        except:
            pass

        print(f'   {flags}')

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
                pass

        print()


def main():
    parser = argparse.ArgumentParser(description='Specify mountain names')
    parser.add_argument('args', nargs='*', help='mountain names')

    parser.add_argument("-m", "--mountainDb", default="mountain_db.py")
    parser.add_argument("-u", "--userRoute", default="user_route_db.py")
    parser.add_argument("-x", "--exclude", action='store', help='excluding mounntain list .csv')

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

    parser.add_argument('-l', '--category', action='store', default=None, help='Specify category e.g.栃木百名山,ぐんま百名山,山梨百名山,日本百名山,日本二百名山,日本三百名山 if necessary')

    parser.add_argument('-o', '--openUrl', action='store_true', default=False, help='specify if you want to open the url')

    args = parser.parse_args()

    minRouteTime = get_min_from_hhmm(args.minRouteTime)
    maxRouteTime = get_min_from_hhmm(args.maxRouteTime)
    minClimbTime = get_min_from_hhmm(args.minClimbTime)
    maxClimbTime = get_min_from_hhmm(args.maxClimbTime)

    db, routes, exclude_uuid, exclude_name = load_resources(
        args.mountainDb,
        args.userRoute,
        args.exclude
    )

    mountains = []
    for m in args.args:
        if not is_mountain_excluded(m, m, exclude_uuid, exclude_name):
            mountains.append(m)

    selected = collect_candidates(
        db,
        routes,
        exclude_uuid,
        exclude_name,
        args.altitudeMin,
        args.altitudeMax,
        minRouteTime,
        maxRouteTime,
        minClimbTime,
        maxClimbTime,
        args.distanceMin,
        args.distanceMax,
        args.elevationMin,
        args.elevationMax,
        args.category,
        mountains
    )

    sort_candidates(selected)

    output_human(selected)

    n = 0
    for m in selected:
        info = m["mountain"]
        if "url" in info:
            url = info["url"]
            if args.openUrl:
                if n>=1:
                    time.sleep(1)
                ExecUtil.open( info["url"] )
                n = n + 1


if __name__ == "__main__":
    main()
