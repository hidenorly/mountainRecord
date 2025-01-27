# mountainRecord

## setup

```
python3 get_mountain_list.py > mountainDic.py
python3 get_mountain_list_yamap.py > mountainDic_yamap.py
python3 mountain_dic_to_json.py
```

## get_recent_record.py

get recent mountain record page's url list of specified mountain names


```
python3 get_recent_record.py --help
usage: get_recent_record.py [-h] [-nd] [-o] [args ...]

Specify mountainNames

positional arguments:
  args            mountain names

options:
  -h, --help      show this help message and exit
  -nd, --urlOnly  specify if you want to print url only
  -o, --openUrl   specify if you want to open the url
```

```example
python3 get_recent_record.py 皇海山
name:皇海山, yomi:すかいさん, altitude:2144m : https://www.yamareco.com/modules/yamainfo/ptinfo.php?ptid=36#reclist_top
name:皇海山, yomi:すかいさん, altitude:2144 : https://yamap.com/mountains/169
```

## get_recent_record2.py

get concrete recent mountain records of specified mountain names with specified conditions

```
python3 get_recent_record2.py --help
usage: get_recent_record2.py [-h] [-nd] [-o] [-n NUMOPEN] [-d FILTERDAYS] [-e EXCLUDE] [-i INCLUDE] [-g ALTITUDEMIN] [-u ALTITUDEMAX] [args ...]

Specify mountainNames

positional arguments:
  args                  mountain names (default: None)

options:
  -h, --help            show this help message and exit
  -nd, --urlOnly        specify if you want to print url only (default: False)
  -o, --openUrl         specify if you want to open the url (default: False)
  -n NUMOPEN, --numOpen NUMOPEN
                        specify if you want to filter the opening article (default: 3)
  -d FILTERDAYS, --filterDays FILTERDAYS
                        specify if you want to filter the acceptable day before (default: 7)
  -e EXCLUDE, --exclude EXCLUDE
                        specify excluding mountain list file e.g. climbedMountains.lst (default: [])
  -i INCLUDE, --include INCLUDE
                        specify including mountain list file e.g. climbedMountains.lst (default: [])
  -g ALTITUDEMIN, --altitudeMin ALTITUDEMIN
                        Min altitude (default: 0)
  -u ALTITUDEMAX, --altitudeMax ALTITUDEMAX
                        Max altitude (default: 9000)
```

```example
python3 get_recent_record2.py 皇海山
```

## get_detail_record.py

Show the concrete record text from the specified url

```
python3 get_detail_record.py --help
usage: get_detail_record.py [-h] [-n] [-f FILTEROUT] [-d DISTANCEMAX] [-s DISTANCEMIN] [-t MAXTIME] [-b MINTIME] [-e ELEVATIONMAX] [-r ELEVATIONMIN]
                            [-p] [-1] [-o] [-c] [-w]
                            [args ...]

Specify mountain detail record urls

positional arguments:
  args                  url(s) (default: None)

options:
  -h, --help            show this help message and exit
  -n, --noOutputIfNone  specify if you want not to print None report (default: False)
  -f FILTEROUT, --filterOut FILTEROUT
                        specify if you want to filter out the field e.g. photo_captions|access (default: )
  -d DISTANCEMAX, --distanceMax DISTANCEMAX
                        specify distance maximum (default: None)
  -s DISTANCEMIN, --distanceMin DISTANCEMIN
                        specify distance minimum (default: None)
  -t MAXTIME, --maxTime MAXTIME
                        specify max climb time e.g. 5:00 (default: None)
  -b MINTIME, --minTime MINTIME
                        specify min climb time e.g. 4:30 (default: None)
  -e ELEVATIONMAX, --elevationMax ELEVATIONMAX
                        specify max elevation (default: None)
  -r ELEVATIONMIN, --elevationMin ELEVATIONMIN
                        specify min elevation (default: None)
  -p, --piston          specify if you want piston record (default: False)
  -1, --oneway          specify if you want non-piston (one-way) record (default: False)
  -o, --openUrl         specify if you want to open the url (default: False)
  -c, --clearCache      specify if you want to execute with clearing cache (default: False)
  -w, --oneline         specify if you want to print as oneline manner (default: False)
```

```example
python3 get_recent_record2.py 皇海山 -nd | xargs python3 get_detail_record.py
```

## get_mountain_info.py

Show mountain info. such as description, category, etc.

```
python3 get_mountain_info.py --help
usage: get_mountain_info.py [-h] [-g ALTITUDEMIN] [-u ALTITUDEMAX] [-c CATEGORY] [-o] [args ...]

Specify mountain names

positional arguments:
  args                  mountain names

options:
  -h, --help            show this help message and exit
  -g ALTITUDEMIN, --altitudeMin ALTITUDEMIN
                        Min altitude
  -u ALTITUDEMAX, --altitudeMax ALTITUDEMAX
                        Max altitude
  -c CATEGORY, --category CATEGORY
                        Specify category e.g.日本百名山|100名山 if necessary
  -o, --openUrl         specify if you want to open the url
```

```example
python3 get_mountain_info.py 皇海山
```

