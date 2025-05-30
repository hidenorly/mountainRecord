#   Copyright 2024, 2025 hidenorly
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

import argparse
import mountainDic
import sys
import subprocess
import shlex
import time
import json
import itertools
import os
from mountainRecordUtil import ExecUtil, MountainRecordUtil


if __name__=="__main__":
	parser = argparse.ArgumentParser(description='Specify mountainNames')
	parser.add_argument('args', nargs='*', help='mountain names')
	parser.add_argument('-nd', '--urlOnly', action='store_true', default=False, help='specify if you want to print url only')
	parser.add_argument('-o', '--openUrl', action='store_true', default=False, help='specify if you want to open the url')

	args = parser.parse_args()
	recUtil = MountainRecordUtil()

	n = 0
	for aMountainName in args.args:
		result = recUtil.getMountainsWithMountainName( aMountainName )
		for aMountain in result:
			n = n + 1
			if args.urlOnly:
				print( aMountain["url"] )
			else:
				print( f'name:{aMountain["name"]}, yomi:{aMountain["yomi"]}, altitude:{aMountain["altitude"]} : {aMountain["url"]}' )
			if args.openUrl:
				if n>=2:
					time.sleep(1)
				result = ExecUtil.open(aMountain["url"])
				#print(result.stdout)
