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

import mountainDic
import mountainDic_yamap
import re
import json

def mountainDicArray_to_Hash(dic, _mountainDic = None):
	mountainUrls = {}
	for aMountain in dic:
		if aMountain["url"]:
			mountainUrls[ aMountain["url"] ] = aMountain

	if not _mountainDic:
		_mountainDic = {}

	for url, aMountain in mountainUrls.items():
		# support alternative mountain name
		mountainName = aMountain["name"]
		mountainNames = set()
		alts = re.split(r'[\（\）、／]', mountainName)
		for alt in alts:
			mountainNames.add( alt )
		# support yomi
		mountainName = str(aMountain["yomi"])
		alts = re.split(r'[\（\）、／]', mountainName)
		for alt in alts:
			mountainNames.add( alt )

		# make the dic
		for mountainName in mountainNames:
			if mountainName:
				if not mountainName in _mountainDic:
					_mountainDic[ mountainName ] = []
				_mountainDic[ mountainName ].append( aMountain )

	return _mountainDic

if __name__=="__main__":
	_mountainDic = {}
	_mountainDic = mountainDicArray_to_Hash( mountainDic.getMountainDic(), _mountainDic )
	_mountainDic = mountainDicArray_to_Hash( mountainDic_yamap.getMountainDic(), _mountainDic )

	with open("mountain_dic.json", 'w', encoding='UTF-8') as f:
		json.dump(_mountainDic, f, indent = 4, ensure_ascii=False)
		f.close()
