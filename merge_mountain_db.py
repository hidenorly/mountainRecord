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

import copy
import importlib.util
import pprint
import sys


def load_py(filename):
    spec = importlib.util.spec_from_file_location("mod", filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return copy.deepcopy(mod.MOUNTAINS)


def weighted_average(v1, n1, v2, n2):
    total = n1 + n2
    if total == 0:
        return 0
    return (v1 * n1 + v2 * n2) / total


def merge_trailhead(dst, src):

    n1 = dst.get("sample_count", 0)
    n2 = src.get("sample_count", 0)

    dst["sample_count"] = n1 + n2

    #
    # climb time
    #
    dst["climb_time_min"] = min(
        dst["climb_time_min"],
        src["climb_time_min"],
    )

    dst["climb_time_max"] = max(
        dst["climb_time_max"],
        src["climb_time_max"],
    )

    dst["climb_time_median"] = round(
        weighted_average(
            dst["climb_time_median"],
            n1,
            src["climb_time_median"],
            n2,
        )
    )

    #
    # distance
    #
    dst["distance_min_km"] = min(
        dst["distance_min_km"],
        src["distance_min_km"],
    )

    dst["distance_max_km"] = max(
        dst["distance_max_km"],
        src["distance_max_km"],
    )

    dst["distance_median_km"] = round(
        weighted_average(
            dst["distance_median_km"],
            n1,
            src["distance_median_km"],
            n2,
        ),
        1,
    )

    #
    # elevation
    #
    dst["elevation_gain_min"] = min(
        dst["elevation_gain_min"],
        src["elevation_gain_min"],
    )

    dst["elevation_gain_max"] = max(
        dst["elevation_gain_max"],
        src["elevation_gain_max"],
    )

    dst["elevation_gain_median"] = round(
        weighted_average(
            dst["elevation_gain_median"],
            n1,
            src["elevation_gain_median"],
            n2,
        )
    )


def merge_mountain(dst, src):

    #
    # URL
    #
    if not dst.get("url") and src.get("url"):
        dst["url"] = src["url"]

    #
    # flags
    #
    flags = set(dst.get("flags", []))
    flags.update(src.get("flags", []))
    dst["flags"] = sorted(flags)

    #
    # trailheads
    #
    for tid, th in src.get("trailheads", {}).items():

        if tid not in dst["trailheads"]:
            dst["trailheads"][tid] = copy.deepcopy(th)
        else:
            merge_trailhead(dst["trailheads"][tid], th)


def merge(data1, data2):

    result = copy.deepcopy(data1)

    for uuid, mountain in data2.items():

        if uuid not in result:
            result[uuid] = copy.deepcopy(mountain)
        else:
            merge_mountain(result[uuid], mountain)

    return result


def output_python(data):

    print("MOUNTAINS = ", end="")
    pprint.pprint(
        data,
        sort_dicts=False,
        width=120,
    )


def main():

    if len(sys.argv) != 3:
        print("usage:")
        print("   python3 merge_mountain_db.py mountain_db.py bkup/mountain_db.py")
        sys.exit(1)

    data1 = load_py(sys.argv[1])
    data2 = load_py(sys.argv[2])

    merged = merge(data1, data2)

    output_python(merged)


if __name__ == "__main__":
    main()