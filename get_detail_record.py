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


class MountainDetailRecordUtil:
	def __init__(self, url):
		self.data = data = self.parseRecentRecord(url)

		self.level = data["level"]
		self.duration = data["duration"]
		self.actual_duration = data["actual_duration"]
		self.rest_duration = data["rest_duration"]
		self.distance = data["distance"]
		self.elavation_gained = data["elevation_gained"]
		self.elavation_lost = data["elevation_lost"]
		self.pace = data["pace"]
		self.weather = data["weather"]
		self.access = data["access"]
		self.course_info = data["course_info"]
		self.impression = data["impression"]
		self.photo_captions = data["photo_captions"]

	def parseRecentRecord(self, recordUrl):
		result = {
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

	args = parser.parse_args()
	for aUrl in args.args:
		anInfo = MountainDetailRecordUtil(aUrl)
		for key, value in anInfo.data.items():
			print(f'{StrUtil.ljust_jp(key, 20)}\t: {value}')
