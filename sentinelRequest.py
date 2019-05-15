#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 10 15:27:35 2017

@author: oarcher


"""
from __future__ import print_function
import os,sys
import numpy as np
import datetime
import requests
from lxml import etree
import logging

logging.basicConfig()
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.INFO)


urlapi='https://scihub.copernicus.eu/apihub/search'

download_scihub_url={  # %s : uuid
    "main" : "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')/$value",
    "alt"  : "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')/",
    "ql"   : "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')/Products('Quicklook')/$value"
    }

xslt='''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="xml" indent="no"/>

<xsl:template match="/|comment()|processing-instruction()">
    <xsl:copy>
      <xsl:apply-templates/>
    </xsl:copy>
</xsl:template>

<xsl:template match="*">
    <xsl:element name="{local-name()}">
      <xsl:apply-templates select="@*|node()"/>
    </xsl:element>
</xsl:template>

<xsl:template match="@*">
    <xsl:attribute name="{local-name()}">
      <xsl:value-of select="."/>
    </xsl:attribute>
</xsl:template>
</xsl:stylesheet>
'''

remove_dom=etree.XSLT(etree.fromstring(xslt))


def download_scihub(filename,user='oarcher', password='nliqt6u3'):
    safe=scihubQuery(filename=filename, user=user, password=password)
    urldl=download_scihub_url['ql'] % safe[filename]['uuid']
    # todo : use wget for downloads
    xmlout=requests.get(urldl,auth=(user,password))
    
    return xmlout


def scihubQuery(date=None,dtime=datetime.timedelta(hours=3) ,lonlat=None, ddeg=0.1 ,filename='S1*', datatake=False, query=None, user='guest', password='guest'):
    """
    query='(platformname:Sentinel-1 AND sensoroperationalmode:WV)' 
    input:
        date: [ start, stop ] 
        if [ date ], dtime will be used to compute start ans stop
        lonlat : [ lon, lat ] or [[lon],[lat]]
    """
    
    q=[]
    
    footprint=""
    datePosition=""
    
    try:
        roi=define_POLYGON(lonlat[0], lonlat[1],ddeg=ddeg)
        footprint=" OR ".join(['(footprint:\"Intersects(POLYGON((%s)))\" )' % poly for poly in roi])
        footprint="(%s)" % footprint
        q.append(footprint)
    except:
        logger.debug("not using lon/lat selection")
        pass
        
    if date:
        try:
            len(date)
        except:
            date=[date]
        if len(date) == 2:
            startdate=date[0].strftime("%Y-%m-%dT%H:%M:%S.000Z")
            stopdate=date[1].strftime("%Y-%m-%dT%H:%M:%S.000Z")
        else:
            startdate=(date[0]-dtime).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            stopdate=(date[0]+dtime).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
        datePosition="(beginPosition:[%s TO %s] OR endPosition:[%s TO %s])" % (startdate , stopdate , startdate, stopdate)
        q.append(datePosition)
        
    q.append("filename:%s" % filename)
    
    if query:
        q.append("(%s)" % query)
    
    str_query = ' AND '.join(q)
    
    logger.debug("query: %s" % str_query)
    
    safes={}
    start=0
    while start >= 0:
        xmlout=requests.get(urlapi,auth=(user,password),params={"start":start,"rows":100,"q":str_query})
        
        try:
            root = remove_dom(etree.fromstring(xmlout.content))
        except:
            try:
                import html2text
                content=html2text.html2text(str(xmlout.content))
            except:
                logger.info("html2text not found. dumping raw html")
                content=xmlout.content
            logger.critical("Error while parsing xml answer")
            logger.critical("query was: %s" % str_query )
            logger.critical("answer is: \n %s" % content)
            return {}
        
        logger.debug("%s" % root.findall(".//subtitle")[0].text )
        #logger.debug("got %d entry starting at %d" % (len(root.findall(".//entry")),start))
        
        if len(root.findall(".//entry")) > 0:
            for entry in root.findall(".//entry"):
                filename=entry.find("str[@name = 'filename']").text
                safe={}
                for strelt in ['footprint','orbitdirection','polarisationmode','uuid','status']:
                    safe[strelt]=entry.find("str[@name = '%s']" % strelt).text
                safes["%s" % filename] = safe
                start+=1
        else:
            start=-1
        
    if datatake:
        logger.debug("Asking for same datatakes")
        for safe in list(safes.keys()):
            takeid=safe.split('_')[-2]
            safe_rad="_".join(safe.split('_')[0:4])
            safes_datatake=scihubQuery(filename='%s_*_*_*_%s_*' % (safe_rad, takeid),user=user,password=password)
            for safe_datatake,value in safes_datatake.items():
                safes[safe_datatake]=value
        

    return safes

def define_POLYGON(lon,lat,ddeg=4.0):
    lat_min = np.min(lat) - ddeg
    if lat_min < -90.:
        lat_min = -90.
    lat_max = np.max(lat) + ddeg
    if lat_max > 90.:
        lat_max = 90.
    lon = np.mod(np.array(lon)+360.,360.)
    lon_min = np.min(lon) - ddeg
    lon_max = np.max(lon) + ddeg  
    if lon_max > 180.:
        lon_max = lon_max - 360.
    if lon_min > 180.:
        lon_min = lon_min - 360.
    POLYGON_l = []
    if (lon_min > 0. and lon_min < 180. and lon_max < 0.):
        POLYGON0 = "%04.2f"%lon_min+' '+ "%04.2f"%lat_min +', '+\
                "%04.2f"%180.0+' '+ "%04.2f"%lat_min +', '+\
                "%04.2f"%180.0+' '+ "%04.2f"%lat_max +', '+\
                "%04.2f"%lon_min+' '+ "%04.2f"%lat_max +', '+\
                "%04.2f"%lon_min+' '+ "%04.2f"%lat_min
        POLYGON_l.append(POLYGON0)
        POLYGON1 = "%04.2f"%-180.0+' '+ "%04.2f"%lat_min +', '+\
                "%04.2f"%lon_max+' '+ "%04.2f"%lat_min +', '+\
                "%04.2f"%lon_max+' '+ "%04.2f"%lat_max +', '+\
                "%04.2f"%-180.0+' '+ "%04.2f"%lat_max +', '+\
                "%04.2f"%-180.0+' '+ "%04.2f"%lat_min
        POLYGON_l.append(POLYGON1)
    else:
        POLYGON = "%04.2f"%lon_min+' '+ "%04.2f"%lat_min +', '+\
                    "%04.2f"%lon_max+' '+ "%04.2f"%lat_min +', '+\
                    "%04.2f"%lon_max+' '+ "%04.2f"%lat_max +', '+\
                    "%04.2f"%lon_min+' '+ "%04.2f"%lat_max +', '+\
                    "%04.2f"%lon_min+' '+ "%04.2f"%lat_min
        POLYGON_l.append(POLYGON)
    return POLYGON_l
       

if __name__ == "__main__":
    import argparse
    
    
    dateformat="%Y-%m-%d %H:%M"
    dtime=3
    filename="S1*"
    ddeg=0.1
    
    description = "Requests SAFE list from scihub"

    parser = argparse.ArgumentParser(description = description)

    parser.add_argument("--user",action="store",default=["guest"],nargs=1,type=str,help="scihub login")
    parser.add_argument("--password",action="store",default=["guest"],nargs=1,type=str,help="scihub password")
    parser.add_argument("--date",action="append",default=None, nargs=1,  type=str,help="date as string. if provided 2 time, first is start, last is stop")
    parser.add_argument("--coord",action="append",default=None, nargs=1, type=str,help="lon,lat of center. if provided more times, a polygon is used")
    parser.add_argument("--filename",action="store",default=[filename],nargs=1,type=str,help="filename, with joker. ex 'S1?_?W_GRD*'. default to %s" % filename)
    parser.add_argument("--query",action="store",default=None,nargs=1,type=str,help="""additionnal query. for exemple 'orbitdirection:ASCENDING AND polarisationmode:"VV VH"'""")
    parser.add_argument("--datatake",action="store_true",help="retrieve the whole datatake (ie adjacent SAFEs)")
    parser.add_argument("--dateformat",action="store",default=[dateformat], nargs=1,  type=str,help="strftime date format. default: %%Y-%%m-%%d %%H:%%M" )
    parser.add_argument("--dtime",action="store",default=[dtime],nargs=1,type=int,help="dtime in hours, if --date has only one date. default to %d" % dtime)
    parser.add_argument("--ddeg", action="store",default=[ddeg],nargs=1,type=float,help="ddeg in deg, if --coord has only one lon,lat. default to %3.2f" % ddeg)
    parser.add_argument("--ql",action="store_true",help="download quicklook")
    parser.add_argument("--debug",action="store_true",help="show debug messages")

    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Activating debug messages")
        import debug
        try:
            import debug
        except:
            pass
    # cat /home/datawork-cersat-public/archive/provider/noaa/mirrors/ftp.emc.ncep.noaa.gov/wd20vxt/hwrf-init/decks/bal142018.dat |  awk '($9 + 0) > 64 {print $3"00 "$8" "$7}' | tr -d , | uniq | sed -r 's/([[:digit:]]+)([[:digit:]])N/\1.\2/' | sed -r 's/([[:digit:]]+)([[:digit:]])S/-\1.\2/' | sed -r 's/([[:digit:]]+)([[:digit:]])E/\1.\2/' | sed -r 's/([[:digit:]]+)([[:digit:]])W/-\1.\2/'
    date = None
    if args.date:
        date=[ datetime.datetime.strptime(d[0],args.dateformat[0]) for d in args.date]
    
    
    lon=[]
    lat=[]
    if args.coord:
        for coord in args.coord:
            strlon,strlat=coord[0].split(',')
            lon.append(float(strlon))
            lat.append(float(strlat))
    
    try:
        query=args.query[0]
    except:
        query=None
        
    
    
    result=scihubQuery(date=date,lonlat=[lon,lat],ddeg=args.ddeg,dtime=datetime.timedelta(hours=args.dtime[0]),filename=args.filename[0],query=query,datatake=args.datatake,user=args.user[0],password=args.password[0])
    for safe in list(result.keys()):
        print(safe)
        #out=download_scihub(safe)
    
