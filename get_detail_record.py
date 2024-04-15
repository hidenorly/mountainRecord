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
import requests
from bs4 import BeautifulSoup
import json
import os
import sys
import subprocess
import re
from datetime import timedelta, datetime
import glob
import shlex
import time


class JsonCache:
  DEFAULT_CACHE_BASE_DIR = os.path.expanduser("~")+"/.cache"
  DEFAULT_CACHE_EXPIRE_HOURS = 1 # an hour
  CACHE_INFINITE = -1

  def __init__(self, cacheDir = None, expireHour = None, numOfCache = None):
  	self.cacheBaseDir = cacheDir if cacheDir else JsonCache.DEFAULT_CACHE_BASE_DIR
  	self.expireHour = expireHour if expireHour else JsonCache.DEFAULT_CACHE_EXPIRE_HOURS
  	self.numOfCache = numOfCache if numOfCache else JsonCache.CACHE_INFINITE

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

  def limitNumOfCacheFiles(self):
  	if self.numOfCache!=self.CACHE_INFINITE:
	  	files = glob.glob(f'{self.cacheBaseDir}/*.json')
	  	files = sorted(files, key=os.path.getmtime, reverse=True)
	  	remove_files = files[self.numOfCache:]
	  	for aRemoveFile in remove_files:
	  		try:
		  		os.remove(aRemoveFile)
		  	except:
		  		pass


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
    self.limitNumOfCacheFiles()


  def isValidCache(self, lastUpdateString):
    result = False
    lastUpdate = datetime.strptime(lastUpdateString, "%Y-%m-%d %H:%M:%S")
    dt_now = datetime.now()
    if self.expireHour == self.CACHE_INFINITE or ( dt_now < ( lastUpdate+timedelta(hours=self.expireHour) ) ):
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

  @staticmethod
  def clearAllCache(cacheId):
  	files = glob.glob(f'{os.path.join(JsonCache.DEFAULT_CACHE_BASE_DIR, cacheId)}/*.json')
  	for aRemoveFile in files:
  		try:
  			os.remove(aRemoveFile)
  		except:
  			pass


class NumUtil:
	def toFloat(inStr):
		pattern = r'(\d+\.\d+)'
		match = re.search(pattern, str(inStr))
		if match:
			return float(match.group(1))
		else:
			pattern = r'(\d+)'
			match = re.search(pattern, str(inStr))
			if match:
				return float(match.group(1))
		return None


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

	def parseRecentRecord(self, soup, result):
		return result


class YamarecoParser(ParserBase):
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

	def parseRecentRecord(self, soup, result):
		if soup:
			date = soup.find('div', class_='record-detail-mainimg-bottom-left-title')
			if date:
				date = date.find('div', class_='date')
				if date:
					date = date.text.strip()
					pos = date.find('〜')
					if pos==-1:
						pos = date.find('[')
					if pos!=-1:
						date = date[0:pos].strip()
					result['date'] = date

			if soup.title:
				title = str(soup.title.string).strip()
				date = result['date']
				pos = date.find('(')
				if pos!=-1:
					date = date[0:pos].strip()
				pos = title.find(date)
				if pos!=-1:
					title = title[0:pos-2]
				result['title'] = title

			level = soup.find('div', class_='record-detail-mainimg-bottom-left-info')
			if level:
				level = level.find('div', class_='level')
				if level:
					level = level.get('title')
					if level:
						level = level.split(':')
						if len(level)==2:
							result['level'] = level[1].strip()

			duration = soup.find('dt', class_='gps')
			if duration:
			    duration = duration.find_next_sibling('dd')
			    if duration:
			        result['duration'] = duration.text.strip()

			course = soup.find('section', class_='record-detail-content-time')
			if course:
				course1 = course.find('dd', class_='time1')
				if course1:
					result['actual_duration'] = course1.text.strip()
				course2 = course.find('dd', class_='time2')
				if course2:
					result['rest_duration'] = course2.text.strip()
				course3 = course.find('dd', class_='time3')
				if course3:
					if result['duration'] == '--:--':
						result['duration'] = course3.text.strip()

			distance = soup.find('dt', class_='distance')
			if distance:
			    distance = distance.find_next_sibling('dd')
			    if distance:
			        result['distance'] = distance.text.strip()

			elevation_gained = soup.find('dt', class_='up')
			if elevation_gained:
				elevation_gained = elevation_gained.find_next_sibling('dd')
				if elevation_gained:
					result['elevation_gained'] = elevation_gained.text.strip()

			elevation_loss = soup.find('dt', class_='down')
			if elevation_loss:
				elevation_loss = elevation_loss.find_next_sibling('dd')
				if elevation_loss:
					result['elevation_lost'] = elevation_loss.text.strip()

			details = soup.find('section', class_='record-detail-content-table')
			if details:
				details = details.find_all('tr')
				for anItem in details:
					text = anItem.get_text().strip()
					if "コース状況" in text:
						course_info = anItem.find_next('td').get_text(separator='\n')
						if course_info:
							result['course_info'] = course_info.strip()
					elif "アクセス" in text:
						access = anItem.find_next('td').get_text().split('\n')
						if access:
							for anAccess in access:
								anAccess = anAccess.strip()
								if anAccess and not "アクセスを調べる" in anAccess and not "my出発地登録" in anAccess:
									result['access'].append(anAccess)
					elif "天候" in text:
						weather = anItem.find_next('td').get_text(separator='\n')
						if weather:
							result['weather'] = weather.strip()

			photos = soup.find_all('div', class_='photo-list-wrap-item-caption')
			for anElement in photos:
				caption = anElement.text.strip()
				if caption:
					result['photo_captions'].append(caption)

			pace = soup.find('div', class_='pace-num')
			if pace:
				pace = pace.get_text().strip()
				if pace:
					result['pace']=pace

			impression = soup.find('div', class_='impression-txt')
			if impression:
				impression = impression.get_text().strip()
				if impression:
					result['impression']=impression

		return result


class YamapParser(ParserBase):
	TARGET_URL = "https://yamap.com"

	def __init__(self):
		super().__init__()

	def parseDate(self, date_text):
		date_parsed = None
		try:
			date_parsed = datetime.strptime(date_text, '%Y年%m月%d日').date()
		except:
			pass
		return date_parsed

	def parseRecentRecord(self, soup, result):
		if soup:
			result["date"] = soup.find('span', class_='ActivityDetailTabLayout__Middle__Date').text.strip()
			result["title"] = soup.find('h1', class_='ActivityDetailTabLayout__Title').text.strip()
			result["actual_duration"] = soup.find('p', id='activity-record-value-duration').text.strip()
			result["distance"] = soup.find('p', id='activity-record-value-distance').text.strip()
			result["elevation_gained"] = soup.find('p', id='activity-record-value-cumulative-up').text.strip()
			result["elevation_lost"] = soup.find('p', id='activity-record-value-cumulative-down').text.strip()
			result["impression"] = soup.find('p', class_='ActivitiesId__Description__Body').text.strip()
			result["impression"] = re.sub(r'\n', ' ', result["impression"])

			# rest time
			rest_time_elements = soup.find_all('div', class_='CourseTimeItem__Total__RestTime')
			rest_hours = 0
			rest_minutes = 0
			for rest_time_element in rest_time_elements:
				time_spans = rest_time_element.find_all('span', class_='CourseTimeItem__Total__Number')
				if len(time_spans) == 1:
					minutes = int(time_spans[0].get_text())
					rest_minutes += minutes
				elif len(time_spans) == 2:
					hours = int(time_spans[0].get_text())
					minutes = int(time_spans[1].get_text())
					rest_hours += hours
					rest_minutes += minutes
				elif len(time_spans) == 4:
					hours = int(time_spans[0].get_text()) * 10 + int(time_spans[1].get_text())
					minutes = int(time_spans[2].get_text()) * 10 + int(time_spans[3].get_text())
					rest_hours += hours
					rest_minutes += minutes
			rest_hours += rest_minutes // 60
			rest_minutes %= 60
			result["rest_duration"] = f"{rest_hours:02}:{rest_minutes:02}"

			# course time
			course_time_text = soup.find('p', class_='CourseConstant__CalculateBy').text.strip()
			if course_time_text:
				course_time = course_time_text.split()[1]
				result["duration"] = course_time

			# photo captions
			photo_captions = []
			photos = soup.find_all('div', class_='ActivitiesId__Photos')
			for photo in photos:
				img_tags = photo.find_all('img')
				for img_tag in img_tags:
					alt_text = img_tag.get('alt', '').strip()
					pos = alt_text.find(" ")
					if pos!=-1:
						alt_text = alt_text[pos+1:].strip()
					if alt_text:
						photo_captions.append(alt_text)
			result["photo_captions"] = photo_captions

		return result


class MountainDetailRecordUtil:
	NUM_OF_CACHE = 1000
	CACHE_ID = "mountainDetailRecord"

	def __init__(self, url):
		cache = JsonCache(os.path.join(JsonCache.DEFAULT_CACHE_BASE_DIR, self.CACHE_ID), JsonCache.CACHE_INFINITE, self.NUM_OF_CACHE)

		self._parser = None
		parser = []
		parser.append( YamarecoParser() )
		parser.append( YamapParser() )
		for aParser in parser:
			if aParser.canHandle(url):
				self._parser = aParser
				break

		self.data = data = cache.restoreFromCache(url)
		if not data:
			self.data = data = self.parseRecentRecord(url)
			if self._parser and data["date"]:
				cache.storeToCache(url, data)

		for key, value in data.items():
			setattr(self, key, value)

		self.distanceNum = NumUtil.toFloat(self.distance)
		self.durationMin = MountainDetailRecordUtil.getMinutesFromHHMM(self.actual_duration)
		self.elavation_up = NumUtil.toFloat(self.elevation_gained)
		self.elavation_down = NumUtil.toFloat(self.elevation_lost)

	@staticmethod
	def getMinutesFromHHMM(timeHHMM):
		result = 0

		if timeHHMM:
			pos = str(timeHHMM).find(":")
			if pos!=-1:
				result = int( timeHHMM[0:pos] ) * 60 + int( timeHHMM[pos+1:] )
			else:
				result = int( timeHHMM )

		return result

	def _createBaseResult(self, recordUrl = None):
		return {
			'url': recordUrl,
			'date': None,
			'title': None,
			'level': None,
			'duration': None,
			'actual_duration': None,
			'rest_duration': None,
			'distance': None,
			'elevation_gained': None,
			'elevation_lost': None,
			'pace': None,
			'weather': None,
			'access': [],
			'course_info': None,
			'impression': None,
			'photo_captions':[],
		}

	def parseRecentRecord(self, recordUrl):
		result = self._createBaseResult(recordUrl)
		soup = None
		try:
			res = requests.get(recordUrl)
			if res:
				soup = BeautifulSoup(res.text, 'html.parser')
		except:
			pass

		if soup and self._parser:
			result = self._parser.parseRecentRecord(soup, result)

		return result

	def isValid(self):
		result = (self.duration != None) and (self.distance != None) and (self.photo_captions)
		return result


class StrUtil:
  @staticmethod
  def ljust_jp(value, length, pad = " "):
    count_length = 0
    for char in value.encode().decode('utf8'):
      if ord(char) <= 255:
        count_length += 1
      else:
        count_length += 2
    return value + pad * (length-count_length)


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
	parser = argparse.ArgumentParser(description='Specify mountain detail record urls', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('args', nargs='*', help='url(s)')
	parser.add_argument('-n', '--noOutputIfNone', action='store_true', default=False, help='specify if you want not to print None report')
	parser.add_argument('-f', '--filterOut', action='store', default="", help='specify if you want to filter out the field e.g. photo_captions|access')
	parser.add_argument('-d', '--distanceMax', action='store', default=None, type=float, help='specify distance maximum')
	parser.add_argument('-s', '--distanceMin', action='store', default=None, type=float, help='specify distance minimum')
	parser.add_argument('-t', '--maxTime', action='store', default=None, help='specify max climb time e.g. 5:00')
	parser.add_argument('-b', '--minTime', action='store', default=None, help='specify min climb time e.g. 4:30')
	parser.add_argument('-e', '--elevationMax', action='store', default=None, type=float, help='specify max elevation')
	parser.add_argument('-r', '--elevationMin', action='store', default=None, type=float, help='specify min elevation')
	parser.add_argument('-p', '--piston', action='store_true', default=False, help='specify if you want piston record')
	parser.add_argument('-1', '--oneway', action='store_true', default=False, help='specify if you want non-piston (one-way) record')
	parser.add_argument('-o', '--openUrl', action='store_true', default=False, help='specify if you want to open the url')
	parser.add_argument('-c', '--clearCache', action='store_true', default=False, help='specify if you want to execute with clearing cache')

	args = parser.parse_args()

	if args.clearCache:
		JsonCache.clearAllCache(MountainDetailRecordUtil.CACHE_ID)

	args.filterOut = args.filterOut.split("|")
	maxDurationMin = MountainDetailRecordUtil.getMinutesFromHHMM(args.maxTime)
	minDurationMin = MountainDetailRecordUtil.getMinutesFromHHMM(args.minTime)

	i = 0
	for aUrl in args.args:
		anInfo = MountainDetailRecordUtil(aUrl)

		# Filter out non-parsable case (login required, etc.)
		if args.noOutputIfNone and not anInfo.isValid():
			continue
		# Filter out distance condition
		if args.distanceMin!=None and anInfo.distance!=None and anInfo.distanceNum<args.distanceMin:
			continue
		# Filter out distance condition
		if args.distanceMax!=None and anInfo.distance!=None and anInfo.distanceNum>args.distanceMax:
			continue
		# Filter out duration
		if anInfo.durationMin and ( (minDurationMin and anInfo.durationMin < minDurationMin ) or (maxDurationMin and anInfo.durationMin > maxDurationMin ) ):
			continue
		# Filter out elevation
		if anInfo.elavation_up and ( (args.elevationMin and anInfo.elavation_up < args.elevationMin ) or (args.elevationMax and anInfo.elavation_up > args.elevationMax ) ):
			continue
		# Filter out piston
		if anInfo.elavation_up and anInfo.elavation_down:
			delta = abs(anInfo.elavation_up-anInfo.elavation_down)
			threshold = min(anInfo.elavation_up,anInfo.elavation_down)*0.1
			if not (args.piston and args.oneway):
				if ( args.piston and delta > threshold ) or ( args.oneway and delta < threshold ):
					continue

		if i>0:
			print("")

		for key, value in anInfo.data.items():
			if not key in args.filterOut:
				if isinstance(value, list):
					print(f'{StrUtil.ljust_jp(key, 20)}\t:')
					for aValue in value:
						print(f'{StrUtil.ljust_jp("", 20)}\t: {aValue}')
				else:
					print(f'{StrUtil.ljust_jp(key, 20)}\t: {value}')

		if args.openUrl:
			if i>=1:
				time.sleep(1)
			ExecUtil.open( aUrl )
		i = i + 1
