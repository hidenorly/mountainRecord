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
import shlex
import time
import json
import itertools
import os
from get_recent_record import MountainRecordUtil
from get_detail_record import StrUtil

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

class ParserMountainInfoBase:
	TARGET_URL = "DUMMY"
	def __init__(self):
		pass

	def canHandle(self, recordUrl):
		return recordUrl.startswith(self.TARGET_URL)

	def _getBaseResult(self):
		return { "altitude":None, "location":None,  "category":[], "description":"" }

	def parseMountainInfo(self, recordUrl):
		result = []

		soup = None
		try:
			res = requests.get(recordUrl)
			soup = BeautifulSoup(res.text, 'html.parser')
		except:
			pass

		if soup:
			result = self._parseMountainInfo(soup, result)

		return result

	def _parseMountainInfo(self, soup, result):
		return result


class MountainInfoUtilYamap(ParserMountainInfoBase):
	TARGET_URL = "https://yamap.com"

	def __init__(self):
		super().__init__()

	def _parseMountainInfo(self, soup, result):
		result = self._getBaseResult()

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

	def __init__(self):
		super().__init__()

	def _parseMountainInfo(self, soup, result):
		result = self._getBaseResult()

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
		if isinstance(value,list):
			print(f"{StrUtil.ljust_jp(key, max_len)}:")
			for _val in value:
				print(f"{" "*max_len}  {_val}")
		else:
			print(f"{StrUtil.ljust_jp(key, max_len)}: {value}")


if __name__=="__main__":
	parser = argparse.ArgumentParser(description='Specify mountainNames')
	parser.add_argument('args', nargs='*', help='mountain names')

	args = parser.parse_args()
	recUtil = MountainRecordUtil()

	parsers = []
	parsers.append( MountainInfoUtilYamareco() )
	parsers.append( MountainInfoUtilYamap() )

	for aMountainName in args.args:
		result = recUtil.getMountainsWithMountainName( aMountainName )
		for aMountain in result:
			for parser in parsers:
				if parser.canHandle(aMountain["url"]):
					_detailInfo = parser.parseMountainInfo(aMountain["url"])
					aMountain.update(_detailInfo)
					dump_per_category(aMountain)
					print("")
