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

import sys
import requests
from bs4 import BeautifulSoup
import re

def getLinks(articleUrl, result=None):
  if result == None:
    result = []
  res = requests.get(articleUrl)
  soup = BeautifulSoup(res.text, 'html.parser')
  rows = soup.find_all('h3', class_='markuplint-ignore-heading-levels css-fsrr9j')
  for row in rows:
    name = row.text.strip()
    yomi = row['aria-label']
    url = row.a['href']
    if url:
      url = str(url).strip()

    next_sibling = row.find_next_sibling('p', class_='css-1gqp30v')
    altitude = None
    if next_sibling:
      _altitude = str(next_sibling.text).strip()
      pos = _altitude.find("標高 ")
      if pos!=-1:
        _altitude = _altitude[pos+3:]
        pos = _altitude.find(" m")
        if pos!=-1:
          altitude = _altitude[:pos]

    result.append( {"name":name, "yomi":yomi, "altitude":altitude, "url":url} )

  return result


if __name__=="__main__":
  baseUrl = "https://yamap.com/mountains/prefectures/a?id="
  result = []
  for i in range(1, 48):
    for j in range(1, 300):
      url = f'{baseUrl}{i}&page={j}'
      _len = len(result)
      result = getLinks(url, result)
      if _len == len(result):
        break

  print("mountainDic_yamap=[")
  for aMountain in result:
    print(f'  {{"name":"{aMountain["name"]}", "yomi":"{aMountain["yomi"]}", "altitude":"{aMountain["altitude"]}", "url":"https://yamap.com{aMountain["url"]}"}},')
  print("]")

  print('''
def getMountainDic:
  return mountainDic_yamap
''')