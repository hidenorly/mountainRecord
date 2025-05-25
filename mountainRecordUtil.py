#   Copyright 2025 hidenorly
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

import json
import os
import sys
import subprocess
import re
from datetime import timedelta, datetime
import glob
import shlex
import time


class MountainRecordUtil:
  MOUNTAIN_DIC_PATH = os.path.join( os.path.dirname(os.path.realpath(__file__)), "mountain_dic.json" )

  def __init__(self):
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
		inStr = re.sub(r',', "", str(inStr))
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
