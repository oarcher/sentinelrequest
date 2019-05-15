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

#download_scihub_url={  # %s : uuid
#    "main" : "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')/$value",
#    "alt"  : "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')/",
#    "ql"   : "https://scihub.copernicus.eu/apihub/odata/v1/Products('%s')/Products('Quicklook')/$value"
#    }

# remove_dom
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


def download_scihub(filename,user='guest', password='guest'):
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
    dateformat="%Y-%m-%dT%H:%M:%S.%fZ"
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
            startdate=date[0].strftime(dateformat)
            stopdate=date[1].strftime(dateformat)
        else:
            startdate=(date[0]-dtime).strftime(dateformat)
            stopdate=(date[0]+dtime).strftime(dateformat)
            
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
                #filename=entry.find("str[@name = 'filename']").text
                safe={}
                
                # get all str objects
                for str_entry in entry.findall("str"):
                    safe[str_entry.attrib['name']]=str_entry.text
                # get all int objects
                for int_entry in entry.findall("int"):
                    safe[int_entry.attrib['name']]=int(int_entry.text)
                # get all date objects
                for date_entry in entry.findall("date"):
                    safe[date_entry.attrib['name']]=datetime.datetime.strptime(date_entry.text,dateformat)
                    
                for link in entry.findall("link"):
                    url_name='url'
                    if 'rel' in link.attrib:
                        url_name="%s_%s" % (url_name, link.attrib['rel'])
                    safe[url_name]=link.attrib['href']
                #safes["%s" % filename] = safe
                
                # append to safes
                for field in safe:
                    if field not in safes:
                        safes[field]=[]
                    safes[field].append(safe[field])
                    
                
                start+=1
        else:
            start=-1
        
    if datatake:
        logger.debug("Asking for same datatakes")
        for safe in list(safes['filename']):
            takeid=safe.split('_')[-2]
            safe_rad="_".join(safe.split('_')[0:4])
            safes_datatake=scihubQuery(filename='%s_*_*_*_%s_*' % (safe_rad, takeid),user=user,password=password)
            idup=safes_datatake['filename'].index(safe)
            for field in safes_datatake:
                del safes_datatake[field][idup]
                safes[field]+=safes_datatake[field]
                
            #for safe_datatake,value in safes_datatake.items():
            #    safes[safe_datatake]=value
        

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
       

