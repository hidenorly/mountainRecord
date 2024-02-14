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
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
import itertools
import os

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

	def parseRecentRecord(self, url):
		result = []
		res = requests.get(url)
		soup = BeautifulSoup(res.text, 'html.parser')
		blocks = soup.select('#reclist .block')
		for block in blocks:
			date_elem = block.select_one('.ft')
			date_text = 'N/A'
			date_parsed = None
			if date_elem:
				date_text = date_elem.text.strip().split('（')[0]
			try:
				date_parsed = datetime.strptime(date_text, '%Y年%m月%d日').date()
			except :
				pass

			level_tag = block.select('.spr1[class*=spr1-level]')
			level = 'N/A'
			if level_tag:
				level_class = [tag['class'][1] for tag in level_tag]
				level_mapping = {
					'spr1-level_C': 'C',
					'spr1-level_B': 'B',
					'spr1-level_A': 'A',
					'spr1-level_S': 'S',
					'spr1-level_D': 'D'
				}
				for cls in level_class:
					if cls in level_mapping:
						level = level_mapping[cls]
						break
			photo = True if block.select_one('.spr1-ico_photo') else False
			route = True if block.select_one('.spr1-ico_route') else False

			url_elem = block.select_one('.title a')
			if url_elem:
				url = url_elem['href']
			else:
				url = 'N/A'

			result.append({
				'date_text': date_text,
				'date': date_parsed,
				'level': level,
				'photo': photo,
				'route': route,
				'url': url
			})
		return result

class ExecUtil:
	@staticmethod
	def _getOpen():
		result = "open"
		if sys.platform.startswith('win'):
			result = "start"
		return result

	@staticmethod
	def open(arg):
		exec_cmd = f'{ExecUtil._getOpen()} {arg}'
		result = subprocess.run(exec_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
		return result


class MountainFilterUtil:
  @staticmethod
  def openCsv( fileName, delimiter="," ):
    result = []
    if os.path.exists( fileName ):
      file = open( fileName )
      if file:
        reader = csv.reader(file, quoting=csv.QUOTE_MINIMAL, delimiter=delimiter)
        for aRow in reader:
          data = []
          for aCol in aRow:
            aCol = aCol.strip()
            if aCol.startswith("\""):
              aCol = aCol[1:len(aCol)]
            if aCol.endswith("\""):
              aCol = aCol[0:len(aCol)-1]
            data.append( aCol )
          result.append( data )
    return result

  @staticmethod
  def isMatchedMountainRobust(arrayData, search):
    result = False
    for aData in arrayData:
      if aData.startswith(search) or search.startswith(aData):
        result = True
        break
    return result

  @staticmethod
  def getSetOfCsvs( csvFiles ):
    result = set()
    csvFiles = csvFiles.split(",")
    for aCsvFile in csvFiles:
      aCsvFile = os.path.expanduser( aCsvFile )
      theSet = set( itertools.chain.from_iterable( MountainFilterUtil.openCsv( aCsvFile ) ) )
      result = result.union( theSet )
    return result

  @staticmethod
  def mountainsIncludeExcludeFromFile( mountains, excludeFile, includeFile ):
    result = set()
    includes = set()
    excludes = set()
    for anExclude in excludeFile:
      excludes =  excludes | MountainFilterUtil.getSetOfCsvs( anExclude )
    for anInclude in includeFile:
      includes = includes | MountainFilterUtil.getSetOfCsvs( anInclude )
    for aMountain in includes:
      mountains.add( aMountain )
    for aMountain in mountains:
      if not MountainFilterUtil.isMatchedMountainRobust( excludes, aMountain ):
        result.add( aMountain )
    return result


if __name__=="__main__":
	parser = argparse.ArgumentParser(description='Specify mountainNames', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('args', nargs='*', help='url encoded strings')
	parser.add_argument('-nd', '--urlOnly', action='store_true', default=False, help='specify if you want to print url only')
	parser.add_argument('-o', '--openUrl', action='store_true', default=False, help='specify if you want to open the url')
	parser.add_argument('-n', '--numOpen', action='store', type=int, default=1, help='specify if you want to filter the opening article')
	parser.add_argument('-f', '--filterLevel', action='store', default="D|C|B|A|S", help='specify if you want to filter the article info level')
	parser.add_argument('-d', '--filterDays', action='store', type=int, default=7, help='specify if you want to filter the acceptable day before')
	parser.add_argument('-e', '--exclude', action='append', default=[], help='specify excluding mountain list file e.g. climbedMountains.lst')
	parser.add_argument('-i', '--include', action='append', default=[], help='specify including mountain list file e.g. climbedMountains.lst')

	args = parser.parse_args()
	recUtil = MountainRecordUtil()
	acceptableInfoLevel = args.filterLevel.split("|")
	today = datetime.now().date()

	mountains = MountainFilterUtil.mountainsIncludeExcludeFromFile( set(args.args), args.exclude, args.include )

	for aMountainName in mountains:
		result = recUtil.getMountainsWithMountainName( aMountainName )
		for aMountain in result:
			results = recUtil.parseRecentRecord( aMountain["url"] )
			n = 0
			for aResult in results:
				if aResult["level"] in acceptableInfoLevel:
					date_diff = today - aResult["date"]
					if date_diff.days < args.filterDays:
						n=n+1
						if n<=args.numOpen:
							url = aResult["url"]
							if args.urlOnly:
								print( url )
							else:
								print( f'name:{aMountain["name"]}, yomi:{aMountain["yomi"]}, altitude:{aMountain["altitude"]} : {url}' )
							if args.openUrl:
								ExecUtil.open( url )
