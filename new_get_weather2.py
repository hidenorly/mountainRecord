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

from get_mountain_info2 import *
from new_get_weather import *

import argparse
import time

def get_weather(provider, latitude, longitude, altitude, dates, time_range):
    query = WeatherQuery(
        lat=latitude,
        lon=longitude,
        altitude=altitude,
        dates=dates,
        time_range=time_range,
    )

    return provider.get_weather(query)



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

    parser.add_argument("-p", "--provider", default="openmeteo")
    parser.add_argument("-wd", "--date")
    parser.add_argument("-dw", "--dateweekend", action="store_true")
    parser.add_argument("-t", "--time")
    parser.add_argument("-H", "--hourly", action="store_true")
    parser.add_argument("-j", "--json", action="store_true")



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
        args.args
    )

    sort_candidates(selected)



    provider = ProviderFactory.create(args.provider)

    dates = DateTimeUtil.parse_target_dates(
        args.date,
        args.dateweekend
    )

    time_range = (
        DateTimeUtil.parse_time_range(args.time)
        if args.time else None
    )

    n = 0
    for m in selected:
        info = m["mountain"]

        latitude = float(info["latitude"])
        longitude = float(info["longitude"])
        altitude = float(info["altitude"])

        response = get_weather(provider, latitude, longitude, altitude, dates, time_range)

        flags = ",".join(info["flags"])

        try:
            print(
                f'{info["mountain_name"]}'
                f'({info["yomi"]})'
                f'({info["altitude"]}m)'
                f'({info["mountain_uuid"]}):'
                f'{info["url"]}'
            )
        except:
            pass

        print(f'   {flags}')


        if args.hourly:
            output = {}
            for day, points in response.hourly.items():
                output[day.isoformat()] = [
                    {
                        **asdict(p),
                        "time": p.time.isoformat()
                    }
                    for p in points
                ]
        else:
            output = {
                d.isoformat(): agg
                for d, agg in response.daily.items()
            }

        if args.json:
            print(
                json.dumps(
                    output,
                    ensure_ascii=False,
                    indent=2
                )
            )
            continue

        if args.hourly:
            for day, rows in output.items():
                print(day)
                for row in rows:
                    print(
                        f"{row['time']} "
                        f"temp={row['temperature_c']:.1f}C "
                        f"rain={row['precipitation_mm']:.1f}mm "
                        f"prob={row['precipitation_probability']}% "
                        f"wind={row['wind_speed_ms']:.1f} "
                        f"gust={row['wind_gust_ms']:.1f} "
                        f"{row['weather_code']}"
                    )
                print()
        else:
            for day, agg in output.items():
                if agg:
                    print_human(
                        datetime.fromisoformat(day).date(),
                        agg
                    )

        print("")







if __name__ == "__main__":
    main()
