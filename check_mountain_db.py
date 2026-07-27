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

from mountain_db import *
import os
import subprocess

MOUNTAIN_INFO = os.path.expanduser("~/bin/get_mountain_info.py")

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True)

if __name__ == "__main__":
	for uuid, m in MOUNTAINS.items():
		if not "url" in m:
			print(f"{m["mountain_name"]}")
			print(run(f"python3 {MOUNTAIN_INFO} -p yamareco {m["mountain_name"]}"))


