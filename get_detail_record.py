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
import re
from datetime import timedelta, datetime


class JsonCache:
  DEFAULT_CACHE_BASE_DIR = os.path.expanduser("~")+"/.cache"
  DEFAULT_CACHE_EXPIRE_HOURS = 1 # an hour
  CACHE_INFINITE = -1

  def __init__(self, cacheDir = None, expireHour = None):
  	self.cacheBaseDir = cacheDir if cacheDir else JsonCache.DEFAULT_CACHE_BASE_DIR
  	self.expireHour = expireHour if expireHour else JsonCache.DEFAULT_CACHE_EXPIRE_HOURS

  def ensureCacheStorage(self):
    if not os.path.exists(self.cacheBaseDir):
      os.makedirs(self.cacheBaseDir)

  def getCacheFilename(self, url):
    result = url
    result = re.sub(r'^https?://', '', result) # remove protocol
    result = re.sub(r'^[a-zA-Z0-9\-_]+\.[a-zA-Z]{2,}', '', result) #remove domain
    result = re.sub(r'[^a-zA-Z0-9._-]', '_', result) #remove non-character
    result = result + ".json"
    if result.startswith("."):
    	result=result[1:]
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


class NumUtil:
	def toFloat(inStr):
		pattern = r'(\d+\.\d+)'
		match = re.search(pattern, str(inStr))
		if match:
			return float(match.group(1))
		else:
			return None

class MountainDetailRecordUtil:
	def __init__(self, url):
		cache = JsonCache(os.path.join(JsonCache.DEFAULT_CACHE_BASE_DIR, "mountainRecord"), JsonCache.CACHE_INFINITE)
		self.data = data = cache.restoreFromCache(url)
		if not data:
			self.data = data = self.parseRecentRecord(url)
			cache.storeToCache(url, data)

		for key, value in data.items():
			setattr(self, key, value)

		self.distanceNum = NumUtil.toFloat(self.distance)


	def parseRecentRecord(self, recordUrl):
		result = {
			'url': recordUrl,
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
		soup = None
		try:
			res = requests.get(recordUrl)
			if res:
				soup = BeautifulSoup(res.text, 'html.parser')
		except:
			pass

		if soup:
			if soup.title:
				result['title'] = str(soup.title.string).strip()
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


if __name__=="__main__":
	parser = argparse.ArgumentParser(description='Specify mountain detail record urls', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('args', nargs='*', help='url(s)')
	parser.add_argument('-n', '--noOutputIfNone', action='store_true', default=False, help='specify if you want not to print None report')
	parser.add_argument('-f', '--filterOut', action='store', default="", help='specify if you want to filter out the field e.g. photo_captions|access')
	parser.add_argument('-s', '--distanceMin', action='store', default=None, type=float, help='specify distance minimum')
	parser.add_argument('-d', '--distanceMax', action='store', default=None, type=float, help='specify distance maximum')

	args = parser.parse_args()
	args.filterOut = args.filterOut.split("|")
	i = 0
	for aUrl in args.args:
		anInfo = MountainDetailRecordUtil(aUrl)

		# Filter out non-parsable case (login required, etc.)
		if args.noOutputIfNone and not anInfo.isValid():
			continue
		# Filter out distance condition
		if args.distanceMin!=None and anInfo.distance!=None and anInfo.distanceNum<=args.distanceMin:
			continue
		# Filter out distance condition
		if args.distanceMax!=None and anInfo.distance!=None and anInfo.distanceNum>=args.distanceMax:
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

		i = i + 1
