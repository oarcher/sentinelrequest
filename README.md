# sentinelRequest

scihub and peps requests from command line and python 

```
% ./sentinelRequest.py --help
usage: sentinelRequest.py [-h] [--user USER] [--password PASSWORD]
                          [--date DATE] [--coord COORD] [--filename FILENAME]
                          [--query QUERY] [--datatake]
                          [--dateformat DATEFORMAT] [--dtime DTIME]
                          [--ddeg DDEG] [--ql] [--debug]

Requests SAFE list from scihub

optional arguments:
  -h, --help            show this help message and exit
  --user USER           scihub login
  --password PASSWORD   scihub password
  --date DATE           date as string. if provided 2 time, first is start,
                        last is stop
  --coord COORD         lon,lat of center. if provided more times, a polygon
                        is used
  --filename FILENAME   filename, with joker. ex 'S1?_?W_GRD*'. default to S1*
  --query QUERY         additionnal query. for exemple
                        'orbitdirection:ASCENDING AND polarisationmode:"VV
                        VH"'
  --datatake            retrieve the whole datatake (ie adjacent SAFEs)
  --dateformat DATEFORMAT
                        strftime date format. default: %Y-%m-%d %H:%M
  --dtime DTIME         dtime in hours, if --date has only one date. default
                        to 3
  --ddeg DDEG           ddeg in deg, if --coord has only one lon,lat. default
                        to 0.10
  --ql                  download quicklook
  --debug               show debug messages
  ```