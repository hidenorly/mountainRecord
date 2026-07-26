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
    return copy.deepcopy(mod.USER_TOZANGUCHI)


def merge(data1, data2):
    result = copy.deepcopy(data1)

    for trailhead_id, entry in data2.items():

        if trailhead_id not in result:
            result[trailhead_id] = copy.deepcopy(entry)
            continue

        dst = result[trailhead_id]

        # warning if trailhead_name is different
        if dst.get("trailhead_name") != entry.get("trailhead_name"):
            print(
                f"WARNING: trailhead_name mismatch for {trailhead_id}: "
                f"'{dst.get('trailhead_name')}' != '{entry.get('trailhead_name')}'",
                file=sys.stderr,
            )

        dst["route_time_min"] = min(
            dst["route_time_min"],
            entry["route_time_min"],
        )

    return result


def output_python(data):
    print("USER_TOZANGUCHI = ", end="")
    pprint.pprint(
        data,
        sort_dicts=False,
        width=120,
    )


def main():
    if len(sys.argv) != 3:
        print(
            "usage: merge_user_route_db.py user_route_db.py bkup/user_route_db.py",
            file=sys.stderr,
        )
        sys.exit(1)

    data1 = load_py(sys.argv[1])
    data2 = load_py(sys.argv[2])

    merged = merge(data1, data2)

    output_python(merged)


if __name__ == "__main__":
    main()