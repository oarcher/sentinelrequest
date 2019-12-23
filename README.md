# sentinelRequest

sentinelRequest can be used to colocate a geodataframe (ie areas, trajectories, buoys, etc ...) with sentinel (1, but also 2 , 3 : all known by scihub)

## Install
```
% pip install git+https://gitlab.ifremer.fr/sarwing/sentinelrequest.git
```

## CLI usage


```python
!sentinelRequest --help
```

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
      --outfile OUTFILE     outfile (ie .csv, .gpkg, .shp ...)
      --outfile_format OUTFILE_FORMAT
                            outfile format. default from file ext. see driver
                            option in geopandas.to_file
      --show                show map with matplotlib


## API usage


```python
%matplotlib inline
import geopandas as gpd
from sentinelRequest import scihubQuery_new as scihubQuery
import datetime
import matplotlib.pyplot as plt
import shapely.wkt as wkt

# get your own credential from  https://scihub.copernicus.eu/dhus
import pickle
user,password = pickle.load(open("credential.pkl","rb"))
```

## user request as a geodataframe
As an example, two area are defined, that overlap in time and area


```python
gdf = gpd.GeoDataFrame({
        "beginposition" : [ datetime.datetime(2018,10,13,0) , datetime.datetime(2018,10,13,6) ],
        "endposition"   : [ datetime.datetime(2018,10,13,18) , datetime.datetime(2018,10,13,21) ],
        "geometry"      : [ wkt.loads("POINT (-5 45)").buffer(5) , wkt.loads("POLYGON ((-12 35, -3 35, -3 45, -12 45, -12 35))")]    
    },index=["area1","area2"])
gdf
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>beginposition</th>
      <th>endposition</th>
      <th>geometry</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>area1</th>
      <td>2018-10-13 00:00:00</td>
      <td>2018-10-13 18:00:00</td>
      <td>POLYGON ((0.00000 45.00000, -0.02408 44.50991,...</td>
    </tr>
    <tr>
      <th>area2</th>
      <td>2018-10-13 06:00:00</td>
      <td>2018-10-13 21:00:00</td>
      <td>POLYGON ((-12.00000 35.00000, -3.00000 35.0000...</td>
    </tr>
  </tbody>
</table>
</div>




```python
help(scihubQuery)
```

    Help on function scihubQuery in module sentinelRequest:
    
    scihubQuery(gdf=None, startdate=None, stopdate=None, date=None, dtime=None, timedelta_slice=datetime.timedelta(days=7), filename='S1*', datatake=0, duplicate=False, query=None, user='guest', password='guest', min_sea_percent=None, fig=None, cachedir=None, cacherefreshrecent=datetime.timedelta(days=7))
        input:
            gdf : None geodataframe with geometry and date
            date: column name if gdf, or datetime object
            dtime : if date is not None, dtime as timedelta object will be used to compute startdate and stopdate 
            startdate : None or column  name in gdf , or datetime object . not used if date and dtime are defined
            stopdate : None or column  name in gdf , or datetime object . not used if date and dtime are defined
            duplicate : if True, will return duplicates safes (ie same safe with different prodid). Default to False
            datatake : number of adjacent safes to return (ie 0 will return 1 safe, 1 return 3, 2 return 5, etc )
            query : '(platformname:Sentinel-1 AND sensoroperationalmode:WV)' 
            cachedir : cache requests for speed up
            cacherefreshrecent : timedelta from now. if requested stopdate is recent, will refresh the cache to let scihub ingest new data
            fig : matplotlib fig handle ( default to None : no plot)
        return :
            a geodataframe with safes from scihub, colocated with input gdf (ie same index)
    



```python
fig = plt.figure(figsize=(10,7))
safes = scihubQuery(
        gdf=gdf,
        min_sea_percent=20, 
        user=user,
        password=password,
        filename='S1?_?W_GRD*.SAFE',
        cachedir='/home1/scratch/oarcher/scihub_cache',
        fig=fig)

```

    INFO:sentinelRequest:from 2018-10-13 00:00:00 to 2018-10-13 21:00:00 : 12 SAFES



![png](README_files/README_9_1.png)


The two user area (green) are merged into a simpliest big one (red), but a colocalization with user area is done , to deselect some safes (in yellow ).

One can notice that there is a not colocated safe (yellow) in the circular area (area2) : it's because, it's not time colocated.

Green safe are safe over land (min_sea_percent).



The result is a geodataframe with most information from scihub:


```python
safes.iloc[0]
```




    acquisitiontype                                                      NOMINAL
    beginposition                                     2018-10-13 06:22:57.315000
    endposition                                       2018-10-13 06:23:22.315000
    filename                   S1B_IW_GRDH_1SDV_20181013T062257_20181013T0623...
    footprint                  POLYGON ((-1.371217 48.818211, -4.953517 49.22...
    format                                                                  SAFE
    gmlfootprint               <gml:Polygon srsName="http://www.opengis.net/g...
    identifier                 S1B_IW_GRDH_1SDV_20181013T062257_20181013T0623...
    ingestiondate                                     2018-10-13 10:00:40.688000
    instrumentname                             Synthetic Aperture Radar (C-band)
    instrumentshortname                                                SAR-C SAR
    lastorbitnumber                                                        13130
    lastrelativeorbitnumber                                                  154
    missiondatatakeid                                                      99368
    orbitdirection                                                    DESCENDING
    orbitnumber                                                            13130
    platformidentifier                                                 2016-025A
    platformname                                                      Sentinel-1
    polarisationmode                                                       VV VH
    productclass                                                               S
    producttype                                                              GRD
    relativeorbitnumber                                                      154
    sensoroperationalmode                                                     IW
    size                                                                 1.65 GB
    slicenumber                                                               16
    status                                                              ARCHIVED
    swathidentifier                                                           IW
    url                        https://scihub.copernicus.eu/apihub/odata/v1/P...
    url_alternative            https://scihub.copernicus.eu/apihub/odata/v1/P...
    url_icon                   https://scihub.copernicus.eu/apihub/odata/v1/P...
    uuid                                    ffac5e34-2e15-4238-9bd9-6bd0c1d6ca89
    timeliness                                                          Fast-24h
    Name: area1, dtype: object



Index from original request are preserved, so it's easy to know the area that belong to a safe


```python
safes.loc['area1']
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>acquisitiontype</th>
      <th>beginposition</th>
      <th>endposition</th>
      <th>filename</th>
      <th>footprint</th>
      <th>format</th>
      <th>gmlfootprint</th>
      <th>identifier</th>
      <th>ingestiondate</th>
      <th>instrumentname</th>
      <th>...</th>
      <th>sensoroperationalmode</th>
      <th>size</th>
      <th>slicenumber</th>
      <th>status</th>
      <th>swathidentifier</th>
      <th>url</th>
      <th>url_alternative</th>
      <th>url_icon</th>
      <th>uuid</th>
      <th>timeliness</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>area1</th>
      <td>NOMINAL</td>
      <td>2018-10-13 06:22:57.315</td>
      <td>2018-10-13 06:23:22.315</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062257_20181013T0623...</td>
      <td>POLYGON ((-1.371217 48.818211, -4.953517 49.22...</td>
      <td>SAFE</td>
      <td>&lt;gml:Polygon srsName="http://www.opengis.net/g...</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062257_20181013T0623...</td>
      <td>2018-10-13 10:00:40.688</td>
      <td>Synthetic Aperture Radar (C-band)</td>
      <td>...</td>
      <td>IW</td>
      <td>1.65 GB</td>
      <td>16</td>
      <td>ARCHIVED</td>
      <td>IW</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>ffac5e34-2e15-4238-9bd9-6bd0c1d6ca89</td>
      <td>Fast-24h</td>
    </tr>
    <tr>
      <th>area1</th>
      <td>NOMINAL</td>
      <td>2018-10-13 06:23:22.317</td>
      <td>2018-10-13 06:23:47.315</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062322_20181013T0623...</td>
      <td>POLYGON ((-1.820918 47.322227, -5.29902 47.732...</td>
      <td>SAFE</td>
      <td>&lt;gml:Polygon srsName="http://www.opengis.net/g...</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062322_20181013T0623...</td>
      <td>2018-10-13 10:03:18.469</td>
      <td>Synthetic Aperture Radar (C-band)</td>
      <td>...</td>
      <td>IW</td>
      <td>1.65 GB</td>
      <td>17</td>
      <td>ARCHIVED</td>
      <td>IW</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>fbfee557-21ac-43d8-8057-71f40895a199</td>
      <td>Fast-24h</td>
    </tr>
    <tr>
      <th>area1</th>
      <td>NOMINAL</td>
      <td>2018-10-13 06:23:47.316</td>
      <td>2018-10-13 06:24:12.314</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062347_20181013T0624...</td>
      <td>POLYGON ((-2.254533 45.824997, -5.636228 46.23...</td>
      <td>SAFE</td>
      <td>&lt;gml:Polygon srsName="http://www.opengis.net/g...</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062347_20181013T0624...</td>
      <td>2018-10-13 10:00:43.034</td>
      <td>Synthetic Aperture Radar (C-band)</td>
      <td>...</td>
      <td>IW</td>
      <td>1.65 GB</td>
      <td>18</td>
      <td>ARCHIVED</td>
      <td>IW</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>b69f2996-bd94-4f57-a4d9-3e1a307ccff2</td>
      <td>Fast-24h</td>
    </tr>
    <tr>
      <th>area1</th>
      <td>NOMINAL</td>
      <td>2018-10-13 06:24:12.316</td>
      <td>2018-10-13 06:24:37.314</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062412_20181013T0624...</td>
      <td>POLYGON ((-2.674236 44.326656, -5.966702 44.73...</td>
      <td>SAFE</td>
      <td>&lt;gml:Polygon srsName="http://www.opengis.net/g...</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062412_20181013T0624...</td>
      <td>2018-10-13 10:00:43.891</td>
      <td>Synthetic Aperture Radar (C-band)</td>
      <td>...</td>
      <td>IW</td>
      <td>1.65 GB</td>
      <td>19</td>
      <td>ARCHIVED</td>
      <td>IW</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>6244c5a5-cf83-4f27-90c4-e9b2e17c39dd</td>
      <td>Fast-24h</td>
    </tr>
    <tr>
      <th>area1</th>
      <td>NOMINAL</td>
      <td>2018-10-13 06:24:37.315</td>
      <td>2018-10-13 06:25:02.315</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062437_20181013T0625...</td>
      <td>POLYGON ((-3.10039 42.829861, -6.308844 43.238...</td>
      <td>SAFE</td>
      <td>&lt;gml:Polygon srsName="http://www.opengis.net/g...</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062437_20181013T0625...</td>
      <td>2018-10-13 10:02:56.026</td>
      <td>Synthetic Aperture Radar (C-band)</td>
      <td>...</td>
      <td>IW</td>
      <td>1.65 GB</td>
      <td>20</td>
      <td>ARCHIVED</td>
      <td>IW</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>ea30fb07-13c8-49eb-b4c3-9f490b92fdef</td>
      <td>Fast-24h</td>
    </tr>
  </tbody>
</table>
<p>5 rows × 32 columns</p>
</div>



Some safe are in both area:


```python
safes[safes.duplicated(['filename'],keep=False)]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>acquisitiontype</th>
      <th>beginposition</th>
      <th>endposition</th>
      <th>filename</th>
      <th>footprint</th>
      <th>format</th>
      <th>gmlfootprint</th>
      <th>identifier</th>
      <th>ingestiondate</th>
      <th>instrumentname</th>
      <th>...</th>
      <th>sensoroperationalmode</th>
      <th>size</th>
      <th>slicenumber</th>
      <th>status</th>
      <th>swathidentifier</th>
      <th>url</th>
      <th>url_alternative</th>
      <th>url_icon</th>
      <th>uuid</th>
      <th>timeliness</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>area1</th>
      <td>NOMINAL</td>
      <td>2018-10-13 06:24:12.316</td>
      <td>2018-10-13 06:24:37.314</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062412_20181013T0624...</td>
      <td>POLYGON ((-2.674236 44.326656, -5.966702 44.73...</td>
      <td>SAFE</td>
      <td>&lt;gml:Polygon srsName="http://www.opengis.net/g...</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062412_20181013T0624...</td>
      <td>2018-10-13 10:00:43.891</td>
      <td>Synthetic Aperture Radar (C-band)</td>
      <td>...</td>
      <td>IW</td>
      <td>1.65 GB</td>
      <td>19</td>
      <td>ARCHIVED</td>
      <td>IW</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>6244c5a5-cf83-4f27-90c4-e9b2e17c39dd</td>
      <td>Fast-24h</td>
    </tr>
    <tr>
      <th>area2</th>
      <td>NOMINAL</td>
      <td>2018-10-13 06:24:12.316</td>
      <td>2018-10-13 06:24:37.314</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062412_20181013T0624...</td>
      <td>POLYGON ((-2.674236 44.326656, -5.966702 44.73...</td>
      <td>SAFE</td>
      <td>&lt;gml:Polygon srsName="http://www.opengis.net/g...</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062412_20181013T0624...</td>
      <td>2018-10-13 10:00:43.891</td>
      <td>Synthetic Aperture Radar (C-band)</td>
      <td>...</td>
      <td>IW</td>
      <td>1.65 GB</td>
      <td>19</td>
      <td>ARCHIVED</td>
      <td>IW</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>6244c5a5-cf83-4f27-90c4-e9b2e17c39dd</td>
      <td>Fast-24h</td>
    </tr>
    <tr>
      <th>area1</th>
      <td>NOMINAL</td>
      <td>2018-10-13 06:24:37.315</td>
      <td>2018-10-13 06:25:02.315</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062437_20181013T0625...</td>
      <td>POLYGON ((-3.10039 42.829861, -6.308844 43.238...</td>
      <td>SAFE</td>
      <td>&lt;gml:Polygon srsName="http://www.opengis.net/g...</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062437_20181013T0625...</td>
      <td>2018-10-13 10:02:56.026</td>
      <td>Synthetic Aperture Radar (C-band)</td>
      <td>...</td>
      <td>IW</td>
      <td>1.65 GB</td>
      <td>20</td>
      <td>ARCHIVED</td>
      <td>IW</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>ea30fb07-13c8-49eb-b4c3-9f490b92fdef</td>
      <td>Fast-24h</td>
    </tr>
    <tr>
      <th>area2</th>
      <td>NOMINAL</td>
      <td>2018-10-13 06:24:37.315</td>
      <td>2018-10-13 06:25:02.315</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062437_20181013T0625...</td>
      <td>POLYGON ((-3.10039 42.829861, -6.308844 43.238...</td>
      <td>SAFE</td>
      <td>&lt;gml:Polygon srsName="http://www.opengis.net/g...</td>
      <td>S1B_IW_GRDH_1SDV_20181013T062437_20181013T0625...</td>
      <td>2018-10-13 10:02:56.026</td>
      <td>Synthetic Aperture Radar (C-band)</td>
      <td>...</td>
      <td>IW</td>
      <td>1.65 GB</td>
      <td>20</td>
      <td>ARCHIVED</td>
      <td>IW</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>https://scihub.copernicus.eu/apihub/odata/v1/P...</td>
      <td>ea30fb07-13c8-49eb-b4c3-9f490b92fdef</td>
      <td>Fast-24h</td>
    </tr>
  </tbody>
</table>
<p>4 rows × 32 columns</p>
</div>


