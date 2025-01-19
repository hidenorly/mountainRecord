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
from get_recent_record import MountainRecordUtil
from get_detail_record import StrUtil, NumUtil, JsonCache


import requests
from bs4 import BeautifulSoup

class ParserMountainInfoBase:
	TARGET_URL = "DUMMY"

	NUM_OF_CACHE = 1000
	CACHE_ID = "mountainInfo"

	def __init__(self, cache):
		self.cache = cache

	def canHandle(self, recordUrl):
		return recordUrl.startswith(self.TARGET_URL)

	def _getBaseResult(self):
		return { "altitude":None, "location":None,  "category":[], "description":"" }

	def parseMountainInfo(self, recordUrl):
		result = self.cache.restoreFromCache(recordUrl)
		if not result:
			result = self._getBaseResult()
			soup = None
			try:
				res = requests.get(recordUrl)
				soup = BeautifulSoup(res.text, 'html.parser')
			except:
				pass

			if soup:
				result = self._parseMountainInfo(soup, result)
				self.cache.storeToCache(recordUrl, result)

		return result

	def _parseMountainInfo(self, soup, result):
		return result


class MountainInfoUtilYamap(ParserMountainInfoBase):
	TARGET_URL = "https://yamap.com"

	def __init__(self, cache):
		super().__init__(cache)

	def _parseMountainInfo(self, soup, result):
		if soup:
			# highlights
			highlights = soup.select('ul.Mountain__BasicInfo__Highlights li')
			if highlights:
				for li in highlights:
					highlight_texts = li.get_text(strip=True)
					result["description"] += f"* {highlight_texts}\n"

			# description
			description = soup.select_one('p.Mountain__BasicInfo__Description span')
			if description:
				description_text = description.get_text(strip=True)
				result["description"] += description_text

			# altitude
			altitude = soup.select_one('p.MountainInformationSlider__Altitude')
			if altitude:
				altitude_text = altitude.get_text(strip=True)
				if altitude_text:
					result["altitude"] = altitude_text

			# category
			area_texts = soup.find_all('a', class_='MountainInformationSlider__Area__Text')
			if area_texts:
				for a in area_texts:
					href = a.get("href")
					if href and href.startswith("/mountains/famous/"):
						result["category"].append( a.get_text(strip=True) )

		return result


class MountainInfoUtilYamareco(ParserMountainInfoBase):
	TARGET_URL = "https://www.yamareco.com/"

	def __init__(self, cache):
		super().__init__(cache)

	def _parseMountainInfo(self, soup, result):
		if soup:
			# category
			links = soup.find_all('a', class_='cate_link ov')
			if links:
				categories = []
				for link in links:
					categories.append(link.get_text(strip=True))
					result["category"] = categories

			# description
			official_area = soup.find('div', {'id': 'official-area'})
			if official_area:
				official_article = official_area.find('div', {'class': 'official-article'})
				if official_article:
					tag = str(official_article)
					pos = tag.find("<h3>")
					if pos!=None:
						tag = tag[0:pos]
						soup_tag = BeautifulSoup(tag, 'html.parser')
						text = soup_tag.get_text(separator=' ', strip=True)
						if text:
							text = str(text).strip()
							if text:
								result["description"] += text
			else:
				fallback = soup.find('div', {'class': 'basic_info_explain mytips'})
				if fallback:
					result["description"] = fallback.get_text(separator=' ', strip=True)

			# altitude
			altitude = soup.find('th', string='標高')
			if altitude:
				altitude = altitude.find_next('td')
				if altitude:
					result["altitude"] = altitude.text.strip()

			# longitude, latitude
			location = soup.find('th', string='場所')
			if location:
				location = location.find_next('td')
				if location:
					result["location"] = location.text.strip()

			return result

def dump_per_category(result):
	max_len = 0
	for key in result.keys():
		max_len = max(max_len, len(key))
	for key, value in result.items():
		if value:
			if isinstance(value,list):
				print(f"{StrUtil.ljust_jp(key, max_len)}:")
				for _val in value:
					print(f"{" "*max_len}  {_val}")
			else:
				print(f"{StrUtil.ljust_jp(key, max_len)}: {value}")


class MountainInfo:
	def __init__(self):
		self.recUtil = recUtil = MountainRecordUtil()
		self.cache = cache = JsonCache(os.path.join(JsonCache.DEFAULT_CACHE_BASE_DIR, ParserMountainInfoBase.CACHE_ID), JsonCache.CACHE_INFINITE, ParserMountainInfoBase.NUM_OF_CACHE)

		self.parsers = parsers = []
		parsers.append( MountainInfoUtilYamareco(cache) )
		parsers.append( MountainInfoUtilYamap(cache) )

	def get(self, mountain_names):
		results = {}

		for aMountainName in mountain_names:
			_mountains = self.recUtil.getMountainsWithMountainName( aMountainName )
			for aMountain in _mountains:
				for parser in self.parsers:
					if parser.canHandle(aMountain["url"]):
						_detailInfo = parser.parseMountainInfo(aMountain["url"])
						aMountain.update(_detailInfo)
						if not aMountainName in results:
							results[aMountainName] = []
						results[aMountainName].append( aMountain )

		return results


	def getWithCondition(self, mountain_names, min_altitude=0, max_altitude=9000, categories=[]):
		results = {}

		for aMountainName in mountain_names:
			_mountains = self.recUtil.getMountainsWithMountainName( aMountainName )
			for aMountain in _mountains:
				altitude = NumUtil.toFloat(aMountain["altitude"])
				if altitude==None or altitude>=min_altitude and altitude<=max_altitude:
					for parser in self.parsers:
						if parser.canHandle(aMountain["url"]):
							_detailInfo = parser.parseMountainInfo(aMountain["url"])
							aMountain.update(_detailInfo)
							if not aMountainName in results:
								results[aMountainName] = []
							is_found = False
							if not categories:
								is_found = True
							if not is_found and categories:
								for category in categories:
									if category in aMountain["category"]:
										is_found = True
										break
									else:
										for _mountain in aMountain["category"]:
											if _mountain.startswith(category):
												is_found = True
												break

							if is_found:
								results[aMountainName].append( aMountain )

		return results




if __name__=="__main__":
	parser = argparse.ArgumentParser(description='Specify mountain names')
	parser.add_argument('args', nargs='*', help='mountain names')

	parser.add_argument('-g', '--altitudeMin', action='store', default=0, type=int, help='Min altitude')
	parser.add_argument('-u', '--altitudeMax', action='store', default=9000, type=int, help='Max altitude')
	parser.add_argument('-c', '--category', action='store', default="", help='Specify category e.g.日本百名山|100名山 if necessary')

	args = parser.parse_args()
	info = MountainInfo()
	categories = []
	if args.category:
		categories=str(args.category).split("|")
	results = info.getWithCondition(args.args, args.altitudeMin, args.altitudeMax, categories)
	for mountain_name, infos in results.items():
		for info in infos:
			dump_per_category(info)
			print("")

