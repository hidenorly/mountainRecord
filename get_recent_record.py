#   Copyright 2024 hidenorly
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

class MountainRecordUtil:
	def __init__(self):
		dic = mountainDic.getMountainDic()

		mountainUrls = {}
		for aMountain in dic:
			if aMountain["url"]:
				mountainUrls[ aMountain["url"] ] = aMountain

			self.mountainDic = {}
			for url, aMountain in mountainUrls.items():
				if not aMountain["name"] in self.mountainDic:
					self.mountainDic[ aMountain["name"] ] = []
				self.mountainDic[ aMountain["name"] ].append( aMountain )

	def getMountainsWithMountainNameFallback(self, mountainName):
		result = []
		for theMountainName, theMountains in self.mountainDic.items():
			for theMountain in theMountains:
				if theMountain["name"].find(mountainName)!=-1 or theMountain["yomi"].find(mountainName)!=-1:
					result.append( theMountain )
		return result


	def getMountainsWithMountainName(self, mountainName):
		result = []
		if mountainName in self.mountainDic:
			result = self.mountainDic[ mountainName ]
		# fallback
		if not result:
			result = self.getMountainsWithMountainNameFallback(mountainName)
		return result

class ExecUtil:
	@staticmethod
	def _getOpen():
		result = "open"
		if sys.platform.startswith('win'):
			result = "start"
		return result

	@staticmethod
	def open(url):
		exec_cmd = f'{ExecUtil._getOpen()} {url}'
		result = subprocess.run(exec_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
		return result


if __name__=="__main__":
	parser = argparse.ArgumentParser(description='Specify mountainNames')
	parser.add_argument('args', nargs='*', help='url encoded strings')
	parser.add_argument('-nd', '--urlOnly', action='store_true', default=False, help='specify if you want to print url only')
	parser.add_argument('-o', '--openUrl', action='store_true', default=False, help='specify if you want to open the url')

	args = parser.parse_args()
	recUtil = MountainRecordUtil()

	for aMountainName in args.args:
		result = recUtil.getMountainsWithMountainName( aMountainName )
		for aMountain in result:
			if args.urlOnly:
				print( aMountain["url"] )
			else:
				print( f'name:{aMountain["name"]}, yomi:{aMountain["yomi"]}, altitude:{aMountain["altitude"]} : {aMountain["url"]}' )
			if args.openUrl:
				result = ExecUtil.open(aMountain["url"])
				#print(result.stdout)
