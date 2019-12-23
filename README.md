# sentinelRequest

scihub and peps requests from command line and python 

```
% pip install git+https://gitlab.ifremer.fr/sarwing/sentinelrequest.git
% sentinelRequest --help
usage: sentinelRequest [-h] [--user USER] [--password PASSWORD]
                          [--date DATE] [--coord COORD] [--filename FILENAME]
                          [--query QUERY] [--datatake]
                          [--dateformat DATEFORMAT] [--dtime DTIME]
                          [--ddeg DDEG] [--ql] [--debug]

sentinelRequest --help
usage: sentinelRequest [-h] [--user USER] [--password PASSWORD] [--date DATE]
                       [--wkt WKT] [--filename FILENAME] [--query QUERY]
                       [--datatake] [--dateformat DATEFORMAT] [--dtime DTIME]
                       [--cachedir CACHEDIR]
                       [--cacherefreshrecent CACHEREFRESHRECENT] [--cols COLS]
                       [--outfile OUTFILE] [--outfile_format OUTFILE_FORMAT]
                       [--show]

Requests SAFE list from scihub

optional arguments:
  -h, --help            show this help message and exit
  --user USER           scihub login
  --password PASSWORD   scihub password
  --date DATE           date as string. if provided 2 time, first is start,
                        last is stop
  --wkt WKT             wkt representation of the region of interest
  --filename FILENAME   filename, with joker. ex 'S1?_?W_GRD*'. default to S1*
  --query QUERY         additionnal query. for exemple
                          'orbitdirection:ASCENDING AND polarisationmode:"VV
                        VH"'
  --datatake            retrieve the whole datatake (ie adjacent SAFEs)
  --dateformat DATEFORMAT
                        strftime date format. default: %Y-%m-%d %H:%M
  --dtime DTIME         dtime in hours, if --date has only one date. default
                        to 3
  --cachedir CACHEDIR   cache dir to speedup requests
  --cacherefreshrecent CACHEREFRESHRECENT
                        ignore cache if date is more recent than n days ago
  --cols COLS           field output, comma separated
  --outfile OUTFILE     outfile
  --outfile_format OUTFILE_FORMAT
                        outfile format. default from file ext. see driver
                        option in geopandas.to_file
  --show                show map with matplotlib
  ```