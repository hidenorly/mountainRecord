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
from datetime import timedelta, datetime
import csv
import json
import itertools
import os
import re
import copy
import time
import shlex

class JsonCache:
  DEFAULT_CACHE_BASE_DIR = os.path.expanduser("~")+"/.cache"
  DEFAULT_CACHE_EXPIRE_HOURS = 1 # an hour

  def __init__(self, cacheDir = None, expireHour = None):
  	self.cacheBaseDir = cacheDir if cacheDir else JsonCache.DEFAULT_CACHE_BASE_DIR
  	self.expireHour = expireHour if expireHour else JsonCache.DEFAULT_CACHE_EXPIRE_HOURS

  def ensureCacheStorage(self):
    if not os.path.exists(self.cacheBaseDir):
      os.makedirs(self.cacheBaseDir)

  def getCacheFilename(self, url):
  	result = url
  	result = re.sub(r'^https?://', '', url)
  	result = re.sub(r'^[a-zA-Z0-9\-_]+\.[a-zA-Z]{2,}', '', result)
  	result = re.sub(r'[^a-zA-Z0-9._-]', '_', result)
  	result = re.sub(r'\.', '_', result)
  	result = re.sub(r'=', '_', result)
  	result = re.sub(r'#', '_', result)
  	result = result + ".json"
  	return result

  def getCachePath(self, url):
    return os.path.join(self.cacheBaseDir, self.getCacheFilename(url))

  def storeToCache(self, url, result):
    self.ensureCacheStorage()
    cachePath = self.getCachePath( url )
    dt_now = datetime.now()
    _result = {
    	"lastUpdate":dt_now.strftime("%Y-%m-%d %H:%M:%S"),
    	"data": result
    }
    with open(cachePath, 'w', encoding='UTF-8') as f:
      json.dump(_result, f, indent = 4, ensure_ascii=False)
      f.close()

  def isValidCache(self, lastUpdateString):
    result = False
    lastUpdate = datetime.strptime(lastUpdateString, "%Y-%m-%d %H:%M:%S")
    dt_now = datetime.now()
    if dt_now < ( lastUpdate+timedelta(hours=self.expireHour) ):
      result = True

    return result

  def restoreFromCache(self, url):
    result = None
    cachePath = self.getCachePath( url )
    if os.path.exists( cachePath ):
	    with open(cachePath, 'r', encoding='UTF-8') as f:
	      _result = json.load(f)
	      f.close()

	    if "lastUpdate" in _result:
	      if self.isValidCache( _result["lastUpdate"] ):
	        result = _result["data"]

    return result

class ParserBase:
	TARGET_URL = "DUMMY"
	def __init__(self):
		pass

	def canHandle(self, recordUrl):
		return recordUrl.startswith(self.TARGET_URL)

	def parseDate(self, date_text):
		date_parsed = None
		try:
			date_parsed = datetime.strptime(date_text, "%Y/%m/%d").date()
		except:
			pass
		return date_parsed

	def parseRecentRecord(self, recordUrl):
		result = []

		soup = None
		try:
			res = requests.get(recordUrl)
			soup = BeautifulSoup(res.text, 'html.parser')
		except:
			pass

		if soup:
			result = self._parseRecentRecord(soup, result)

		return result

	def _parseRecentRecord(self, soup, result):
		return result


class MountainRecordUtilYamap(ParserBase):
	TARGET_URL = "https://yamap.com"

	def __init__(self):
		super().__init__()

	def parseDate(self, date_text):
		date_parsed = None
		try:
			date_parsed = datetime.strptime(date_text, "%Y.%m.%d").date()
		except:
			pass
		return date_parsed

	def _parseRecentRecord(self, soup, result):
		if soup:
			activities = soup.find_all('article', class_='MountainActivityItem')
			if activities:
				for activity in activities:
					date_text = 'N/A'
					date_parsed = None
					title = activity.find('h3', class_='MountainActivityItem__Heading')
					if title:
						title = title.text.strip()
					_date = activity.find('span', class_='MountainActivityItem__Date')
					if _date:
						_date = _date.text.strip()
					duration = activity.find_all('span', class_='ActivityCounters__Count__Record')
					if duration:
						duration = duration[0].text.strip()
					distance = activity.find_all('span', class_='ActivityCounters__Count__Record')
					if distance:
						if len(distance)>=2:
							distance = distance[1].text.strip().split()[0]
					elevation = activity.find_all('span', class_='ActivityCounters__Count__Record')
					if elevation:
						if len(elevation)>=3:
							elevation=elevation[2].text.strip().split()[0]
					url = activity.find('a', class_='MountainActivityItem__Thumbnail')
					if url:
						url = "https://yamap.com"+url['href']

					if _date:
						date_text = _date.split('(')[0]
						date_parsed = self.parseDate(date_text)

					aData = {
						"title": title,
						'date_text': date_text,
						'date': date_parsed,
						"duration": duration,
						"distance": distance,
						"elevation": elevation,
						"url": url
					}

					if aData['date'] and aData['url']!="N/A":
						result.append( aData )
		return result

class MountainRecordUtilYamareco(ParserBase):
	TARGET_URL = "https://www.yamareco.com/"

	def __init__(self):
		super().__init__()

	def parseDate(self, date_text):
		date_parsed = None
		try:
			date_parsed = datetime.strptime(date_text, '%Y年%m月%d日').date()
		except:
			pass
		return date_parsed

	def _parseRecentRecord(self, soup, result):
		if soup:
			blocks = soup.select('#reclist .block')
			for block in blocks:
				date_elem = block.select_one('.ft')
				date_text = 'N/A'
				date_parsed = None
				if date_elem:
					date_text = date_elem.text.strip().split('（')[0]
					date_parsed = self.parseDate(date_text)

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
				title = ""
				if url_elem:
					url = url_elem['href']
					title = url_elem.text.strip()
				else:
					url = 'N/A'

				aData = {
					"title": title,
					'date_text': date_text,
					'date': date_parsed,
					'level': level,
					'photo': photo,
					'route': route,
					'url': url
				}
				if aData['date'] and aData['url']!="N/A":
					result.append( aData )

		return result



class MountainRecordUtil:
	MOUNTAIN_DIC_PATH = os.path.join( os.path.dirname(os.path.realpath(__file__)), "mountain_dic.json" )

	def __init__(self):
		self.cache = JsonCache(os.path.join(JsonCache.DEFAULT_CACHE_BASE_DIR, "mountainRecord"), 1)

		parser = self.parser = []
		parser.append( MountainRecordUtilYamareco() )
		parser.append( MountainRecordUtilYamap() )

		self.mountainDic = {}

		with open(self.MOUNTAIN_DIC_PATH, 'r', encoding='UTF-8') as f:
			self.mountainDic = json.load(f)
			f.close()

	def getMountainsWithMountainNameFallback(self, mountainName):
		result = {}
		for theMountainName, theMountains in self.mountainDic.items():
			for theMountain in theMountains:
				if theMountain["name"].find(mountainName)!=-1 or theMountain["yomi"].find(mountainName)!=-1:
					result[theMountain["name"]] = theMountain

		return result.values()


	def getMountainsWithMountainName(self, mountainName):
		result = []
		if mountainName in self.mountainDic:
			result = self.mountainDic[ mountainName ]
		# fallback
		if not result:
			result = self.getMountainsWithMountainNameFallback(mountainName)
		return result


	def _getCacheAwareData(self, result):
		_result = []

		if result:
			for aResult in result:
				_aResult = copy.copy(aResult)
				del _aResult['date'] # remove non-serializable data
				_result.append(_aResult)

		return _result

	def _ensureRestoredDataFromCache(self, _result, parser):
		result = []

		for aResult in _result:
			if aResult['date_text'] and aResult['date_text']!="N/A":
				aResult['date'] = parser.parseDate( aResult['date_text'] )
				if aResult['date']:
					result.append(aResult)

		return result

	def parseRecentRecord(self, recordUrl):
		result = []

		parser = None
		for _parser in self.parser:
			if _parser.canHandle(recordUrl):
				parser = _parser
				break

		if parser:
			# try to get cache
			_result = self.cache.restoreFromCache(recordUrl)
			if _result:
				# cache is found
				result = self._ensureRestoredDataFromCache(_result, parser)
			else:
				# cache is NOT found
				result = parser.parseRecentRecord(recordUrl)
				if result:
					# store to cache
					_result = self._getCacheAwareData(result)
					if _result:
						self.cache.storeToCache(recordUrl, _result)

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

  @staticmethod
  def getAltitude( altitude ):
  	result = 0
  	pos = altitude.find("m")
  	if pos!=-1:
	  	altitude = altitude[0:pos]
  	try:
  		result = float(altitude)
  	except:
  		pass
  	return int(result)


class ExecUtil:
  @staticmethod
  def _getOpen():
    result = "open"
    if sys.platform.startswith('win'):
      result = "start"
    return result

  @staticmethod
  def open(url):
    exec_cmd = f'{ExecUtil._getOpen()} {shlex.quote(url)}'
    result = subprocess.run(exec_cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    return result


if __name__=="__main__":
	parser = argparse.ArgumentParser(description='Specify mountainNames', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('args', nargs='*', help='url encoded strings')
	parser.add_argument('-nd', '--urlOnly', action='store_true', default=False, help='specify if you want to print url only')
	parser.add_argument('-o', '--openUrl', action='store_true', default=False, help='specify if you want to open the url')
	parser.add_argument('-n', '--numOpen', action='store', type=int, default=3, help='specify if you want to filter the opening article')
	parser.add_argument('-d', '--filterDays', action='store', type=int, default=7, help='specify if you want to filter the acceptable day before')
	parser.add_argument('-e', '--exclude', action='append', default=[], help='specify excluding mountain list file e.g. climbedMountains.lst')
	parser.add_argument('-i', '--include', action='append', default=[], help='specify including mountain list file e.g. climbedMountains.lst')

	parser.add_argument('-g', '--altitudeMin', action='store', default=0, type=int, help='Min altitude')
	parser.add_argument('-u', '--altitudeMax', action='store', default=9000, type=int, help='Max altitude')

	args = parser.parse_args()
	recUtil = MountainRecordUtil()
	today = datetime.now().date()

	mountains = MountainFilterUtil.mountainsIncludeExcludeFromFile( set(args.args), args.exclude, args.include )
	mountainList=[]
	for aMountainName in mountains:
		mountainList.extend( recUtil.getMountainsWithMountainName( aMountainName ) )
	mountainList = sorted(mountainList, key=lambda x: ( MountainFilterUtil.getAltitude(x["altitude"]), x["name"] ), reverse=True)

	for aMountain in mountainList:
		altitude = MountainFilterUtil.getAltitude( aMountain["altitude"] )
		if altitude>=args.altitudeMin and altitude<=args.altitudeMax:
			results = recUtil.parseRecentRecord( aMountain["url"] )
			n = 0
			for aResult in results:
				if aResult and ("date" in aResult) and aResult["date"]:
					date_diff = today - aResult["date"]
					if date_diff.days < args.filterDays:
						n=n+1
						if n<=args.numOpen:
							url = aResult["url"]
							if args.urlOnly:
								print( url )
							else:
								print( f'name:{aMountain["name"]}, yomi:{aMountain["yomi"]}, altitude:{altitude} : {url} : {aResult["date_text"]} : {aResult["title"]}' )
							if args.openUrl:
								if n>=2:
									time.sleep(1)
								ExecUtil.open( url )
