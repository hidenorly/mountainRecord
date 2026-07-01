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
import math
from datetime import date, timedelta

from new_get_weather import WeatherQuery, ProviderFactory

UNACCEPTABLE_WEATHER = {"rain", "snow", "thunder"}

WEATHER_CACHE = {}


def load_module(path):
    spec = importlib.util.spec_from_file_location("mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_resources(mountainDb, userRoute, exclude):
    db = load_module(mountainDb)
    routes = load_module(os.path.expanduser(userRoute))

    exclude_path = None
    if exclude:
        exclude_path = os.path.expanduser(str(exclude))

    exclude_uuid, exclude_name = load_excludes(
        exclude_path,
        db.MOUNTAINS
    )

    return db, routes, exclude_uuid, exclude_name


def load_excludes(path, mountains):
    exclude_uuid = set()
    exclude_name = set()

    if path:
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
    result = True

    if minv is not None and v < minv:
        result = False

    if maxv is not None and v > maxv:
        result = False

    return result


def get_hhmm_from_min(minutes):
    result = str(minutes)

    try:
        hh = int(minutes / 60)
        mm = int(minutes) - hh * 60
        result = f"{hh:02d}:{mm:02d}"
    except:
        pass

    return result


def get_min_from_hhmm(hhmm):
    result = None # should None. this is used by filter_range

    if hhmm:
        _hhmm = str(hhmm).split(":")
        try:
            hh = int(_hhmm[0])
            mm = int(_hhmm[1])
            result = hh * 60 + mm
        except:
            result = int(str(hhmm))

    return result


def parse_mmdd(token, today):
    month, day = map(int, token.split("/"))
    result = date(today.year, month, day)

    if result < today:
        result = date(today.year + 1, month, day)

    return result


def parse_weather_dates(date_spec, weekend):
    today = date.today()
    result = []

    if weekend:
        wd = today.weekday()

        if wd <= 4:
            sat = today + timedelta(days=(5 - wd))
            result.extend([sat, sat + timedelta(days=1)])
        elif wd == 5:
            result.extend([today, today + timedelta(days=1)])
        else:
            result.extend([
                today,
                today + timedelta(days=6),
                today + timedelta(days=7)
            ])

    if date_spec:
        for token in date_spec.split(","):
            token = token.strip()
            if token:
                result.append(parse_mmdd(token, today))

    if not result:
        result = [today]

    return sorted(set(result))


def round_by_mesh(lat, lon, mesh_km):
    deg_lat = mesh_km / 111.0
    deg_lon = mesh_km / 111.0

    lat2 = round(lat / deg_lat) * deg_lat
    lon2 = round(lon / deg_lon) * deg_lon

    return lat2, lon2


def bucket_altitude(alt):
    return int(round(alt / 100.0) * 100)


def cached_get_weather(provider, query, use_mesh=False, mesh_km=10):
    lat = query.lat
    lon = query.lon
    altitude = query.altitude

    if use_mesh:
        provider_mesh = provider.get_mesh_size_km()
        mesh = max(mesh_km, provider_mesh)
        lat, lon = round_by_mesh(lat, lon, mesh)
        altitude = bucket_altitude(altitude)

    key = (
        provider.__class__.__name__,
        lat,
        lon,
        altitude,
        tuple(query.dates),
        query.time_range
    )

    result = None

    if key in WEATHER_CACHE:
        result = WEATHER_CACHE[key]
    else:
        q = WeatherQuery(
            lat=lat,
            lon=lon,
            altitude=altitude,
            dates=query.dates,
            time_range=query.time_range
        )
        result = provider.get_weather(q)
        WEATHER_CACHE[key] = result

    return result


def summit_weather_ok(provider, mountain, target_date, dates, startHour, duration_hour):
    result = True

    mountain_top_time = int(min(23, startHour + duration_hour*0.6))

    query = WeatherQuery(
        lat=mountain["latitude"],
        lon=mountain["longitude"],
        altitude=mountain["altitude"],
        dates=dates,
        time_range=(mountain_top_time, mountain_top_time)
    )

    response = cached_get_weather(provider, query, False)

    if target_date in response.daily:
        summary = response.daily.get(target_date)
        if not summary:
            result = False

        weather = set(summary["weather"])
        if weather & UNACCEPTABLE_WEATHER:
            result = False

    return result


def trailhead_weather_ok(provider, mountain, trailhead, target_date, dates, pace, startHour, mesh_km):
    result = True

    climb_min = trailhead["climb_time_min"]
    duration_hour = max(1, int((climb_min * pace) / 60) + 1)

    alt = mountain["altitude"] - trailhead["elevation_gain_min"]
    if alt < 0:
        alt = mountain["altitude"] / 2

    query = WeatherQuery(
        lat=trailhead["latitude"],
        lon=trailhead["longitude"],
        altitude=alt,
        dates=dates,
        time_range=(startHour, min(23, startHour + duration_hour))
    )

    response = cached_get_weather(provider, query, True, mesh_km)

    if target_date in response.daily:
        summary = response.daily.get(target_date)
        if not summary:
            result = False

        weather = set(summary["weather"])
        if weather & UNACCEPTABLE_WEATHER:
            result = False

    return result


def is_mountain_excluded(mountain_uuid, mountain, exclude_uuid, exclude_name):
    result = False

    if mountain_uuid in exclude_uuid:
        result = True

    if mountain["mountain_name"] in exclude_name:
        result = True

    return result


def filter_trailhead(th, routes, minRouteTime, maxRouteTime, minClimbTime, maxClimbTime, distanceMin, distanceMax, elevationMin, elevationMax):
    result = None
    tid = th["trailhead_id"]

    if tid in routes.USER_TOZANGUCHI:
        is_Ok = True

        try:
            route_time = routes.USER_TOZANGUCHI[tid]["route_time_min"]
            is_Ok = is_Ok and filter_range(route_time, minRouteTime, maxRouteTime)

            climb_time = th["climb_time_min"]
            is_Ok = is_Ok and filter_range(climb_time, minClimbTime, maxClimbTime)

            distance = th["distance_min_km"]
            is_Ok = is_Ok and filter_range(distance, distanceMin, distanceMax)

            elevation = th["elevation_gain_min"]
            is_Ok = is_Ok and filter_range(elevation, elevationMin, elevationMax)
        except:
            pass

        if is_Ok:
            result = {
                "route_time": route_time,
                "data": th
            }

    return result



def collect_candidates(db, routes, exclude_uuid, exclude_name, altitudeMin, altitudeMax, minRouteTime, maxRouteTime, minClimbTime, maxClimbTime, distanceMin, distanceMax, elevationMin, elevationMax):
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
            altitudeMin,
            altitudeMax
        ):
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


def filter_candidates_by_weather(selected, db, routes, weatherProvider, target_date, dates, pace, startHour, topN, mesh_km):
    result = []
    provider = ProviderFactory.create(weatherProvider)
    preliminary = []

    for row in selected:
        if len(result)<topN:
            mountain = row["mountain"]
            trailheads = []

            max_climb = max(x["data"]["climb_time_min"] for x in row["trailheads"])
            duration_hour = max(1, int((max_climb * pace) / 60) + 1)

            summit_ok = summit_weather_ok(
                provider, mountain,
                target_date, dates,
                startHour, duration_hour
            )

            if not summit_ok:
                continue

            for th in row["trailheads"]:
                ok = trailhead_weather_ok(
                    provider,
                    mountain,
                    th["data"],
                    target_date,
                    dates,
                    pace,
                    startHour,
                    mesh_km
                )

                if ok:
                    trailheads.append(th)

            if trailheads:
                result.append({
                    "best_route": row["best_route"],
                    "mountain": mountain,
                    "trailheads": trailheads
                })

    return result


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
                pass

        print()


def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

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

    parser.add_argument("-nn", action="store_true")
    parser.add_argument("-nw", action="store_true", help='No weather filter')

    parser.add_argument("-wd", "--date", help='specify date e.g. 2/14,2/16-2/17')
    parser.add_argument("-dw", "--weekend", action="store_true", help='specify if weekend (Saturday and Sunday)')
    parser.add_argument("-s", "--startHour", type=int, default=7, help='climbing starting time')
    parser.add_argument("--pace", type=float, default=0.8, help='climbing pace -1.0')
    parser.add_argument("--weatherProvider", default="openmeteo")
    parser.add_argument("--top", type=int, default=10, help='Specify the number of mountain candidates')
    parser.add_argument("--mesh-km", type=float, default=5.0)

    return parser.parse_args()


def main():
    args = parse_args()

    minRouteTime = get_min_from_hhmm(args.minRouteTime)
    maxRouteTime = get_min_from_hhmm(args.maxRouteTime)
    minClimbTime = get_min_from_hhmm(args.minClimbTime)
    maxClimbTime = get_min_from_hhmm(args.maxClimbTime)

    db, routes, exclude_uuid, exclude_name = load_resources(
        args.mountainDb,
        args.userRoute,
        args.exclude
    )
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
    )
    sort_candidates(selected)

    if args.nw:
        if args.nn:
            output_nn(selected)
        else:
            output_human(selected)
    else:
        dates = parse_weather_dates(args.date, args.weekend)

        for target_date in dates:
            if not args.nn:
                print(f"# {target_date}")
            date_selected = filter_candidates_by_weather(
                selected,
                db,
                routes,
                args.weatherProvider,
                target_date,
                dates,
                args.pace,
                args.startHour,
                args.top,
                args.mesh_km
            )

            if args.nn:
                output_nn(date_selected)
            else:
                output_human(date_selected)


if __name__ == "__main__":
    main()