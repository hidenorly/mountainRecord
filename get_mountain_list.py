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
  rows = soup.select('table.ptlist tbody tr')
  for row in rows:
    name = str(row.select_one('td:nth-of-type(2) a').text).strip()
    yomi = str(row.select_one('td:nth-of-type(2) span.f-sm').text).strip()
    yomi = re.sub(r'（', '', yomi).strip()
    yomi = re.sub(r'）', '', yomi).strip()
    altitude = str(row.select_one('td:nth-of-type(3)').text).strip()
    url = row.select_one('a.btn.btn-success.btn-xs')
    if url:
      url = str(url['href']).strip()
    result.append( {"name":name, "yomi":yomi, "altitude":altitude, "url":url} )

  return result


if __name__=="__main__":
  baseUrl = "https://www.yamareco.com/modules/yamainfo/ptlist.php?groupid="
  lists = [1, 2, 3, 7, 11, 20, 29, 38, 39, 133]
  result = []
  for i in lists:
    url = f'{baseUrl}{i}'
    result = getLinks(url, result)

  print("mountainDic=[")
  for aMountain in result:
    print(f'  {{"name":"{aMountain["name"]}", "yomi":"{aMountain["yomi"]}", "altitude":"{aMountain["altitude"]}", "url":"{aMountain["url"]}"}},')
  print("]")

  print('''
def getMountainDic():
  return mountainDic
''')