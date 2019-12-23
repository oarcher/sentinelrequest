from __future__ import print_function
import os,sys
import datetime
import requests
from lxml import etree
import logging
from collections import OrderedDict
import hashlib
from io import StringIO
import geopandas as gpd
import pandas as pd
import shapely.wkt as wkt
import shapely.ops as ops 
from shapely.geometry import MultiPolygon 

logging.basicConfig()
logger = logging.getLogger("sentinelRequest")
if sys.gettrace():
    logger.setLevel(logging.DEBUG)
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)
else:
    logger.setLevel(logging.INFO)

#all wkt objects feeded to scihub will keep rounding_precision digits (2 = 0.01 )
#this will allow to not have too long requests
rounding_precision=2


answer_fields=[u'acquisitiontype', u'beginposition', u'endposition', u'filename',
       u'footprint', u'format', u'gmlfootprint', u'identifier',
       u'ingestiondate', u'instrumentname', u'instrumentshortname',
       u'lastorbitnumber', u'lastrelativeorbitnumber', u'missiondatatakeid',
       u'orbitdirection', u'orbitnumber', u'platformidentifier',
       u'platformname', u'polarisationmode', u'productclass', u'producttype',
       u'relativeorbitnumber', u'sensoroperationalmode', u'size',
       u'slicenumber', u'status', u'swathidentifier', u'url',
       u'url_alternative', u'url_icon', u'uuid']


dateformat="%Y-%m-%dT%H:%M:%S.%fZ"
dateformat_alt="%Y-%m-%dT%H:%M:%S"

urlapi='https://scihub.copernicus.eu/apihub/search'

# earth as multi poly
earth = MultiPolygon(list(gpd.read_file(gpd.datasets.get_path('naturalearth_lowres')).geometry )).buffer(0)
# valid coords
plan_map=wkt.loads("POLYGON ((-180 -90, -180 90, 180 90, 180 -90, -180 -90))")

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

def shape180(lon,lat):
    """shapely shape to -180 180 (for shapely.ops.transform)"""
    import numpy as np
    orig_type=type(lon)
    
    lon = np.array(lon) % 360 
    change = lon>180
    
    lon[change]=lon[change]-360

    # check if 180 should be changed to -180
    if np.sum(lon[lon != 180.0]) <0:
        lon[lon == 180.0] = -180.0

    return tuple([(orig_type)(lon) ,lat])

def split_boundaries(shape):
    """
    A map is a plane representation of a sphere, so a shape can be outside the map, but on the sphere. 
    ie lon=-181 is outside the map -180 -> 180 
    split_boundaries return a polygon collection from a polygon that are all on the map
    """
    
    from shapely.ops import transform
    from shapely.geometry import MultiPolygon
    try:
        # shape is a multi shape
        shapes_list = list(shape)
    except TypeError:
        shapes_list = [shape]
    
    shapes_split_in = []
    shapes_split_out = []
    shapes_non_overlap = []
    for s in shapes_list:   
        if s.overlaps(plan_map):
            logger.debug("shape %s is outside the map" % shape)
            shape_in=s.intersection(plan_map)
            shape_out=s.difference(plan_map)
            shape_out=transform(shape180, shape_out)
            shapes_split_in.append(shape_in)
            shapes_split_out.append(shape_out)
        else:
            shapes_non_overlap.append(s)

    shape=ops.cascaded_union(shapes_split_in + shapes_split_out + shapes_non_overlap)
    return shape

def scihubQuery_raw(str_query, user='guest', password='guest', cachedir=None):
    """
    real scihub query, as done on https://scihub.copernicus.eu/dhus/#/home
    but with cache handling
    
    return a geodataframe with responses
    """
    
    retry_init = 3
    
    safes=gpd.GeoDataFrame(columns=answer_fields,geometry='footprint')
    start=0
    count=1 # arbitrary count > start
    retry=retry_init
    
    if cachedir and not os.path.exists(cachedir):
        os.makedirs(cachedir)
    
    while start < count:
        params=OrderedDict([("start" ,start ), ("rows", 100), ("q",str_query)])
        root=None
        cachefile=None
        if cachedir is not None:
            md5request=hashlib.md5(("%s" % params).encode('utf-8')).hexdigest()
            cachefile=os.path.join(cachedir,md5request)
            if os.path.exists(cachefile):
                logger.debug("reading from cachefile %s" % cachefile)
                try:
                    with open(cachefile, 'a'):
                        os.utime(cachefile, None)
                except Exception as e:
                    logger.warning('unable to touch %s : %s' % (cachefile , str(e) ) )
                    
                try:
                    root = remove_dom(etree.parse(cachefile))
                except Exception as e:
                    logger.warning('removing invalid cachefile %s : %s' % (cachefile,str(e)))
                    os.unlink(cachefile)
                    root=None
                
        
        if root is None:
            # request not cached
            xmlout=requests.get(urlapi,auth=(user,password),params=params)
        
            try:
                root = remove_dom(etree.fromstring(xmlout.content))
            except:
                try:
                    import html2text
                    content=html2text.html2text(str(xmlout.content))
                except:
                    logger.info("html2text not found. dumping raw html")
                    content=str(xmlout.content)
                    
                if 'Timeout occured while waiting response from server' in content:
                    retry-=1
                    logger.warning('Timeout while processing request : %s' % str_query)
                    logger.warning('left rerty : %s' % retry)
                    if retry == 0:
                        raise ConnectionError('Giving up')
                    continue
                    
                    
                logger.critical("Error while parsing xml answer")
                logger.critical("query was: %s" % str_query )
                logger.critical("answer is: \n %s" % content)
                raise ValueError('scihub query error')
            
            if cachefile is not None:
                try:
                    with open(cachefile,'wb') as f:
                        f.write(etree.tostring(root, pretty_print=True))
                except Exception as e:
                    logger.warning('unable to write cachefile %s : %s' % (cachefile, str(e)))
                
            
        
        #<opensearch:totalResults>442</opensearch:totalResults>\n
        try:
            count=int(root.find(".//totalResults").text)
        except:
            # there was an error in request
            if cachefile is not None:
                os.unlink(cachefile)
            
            logger.critical("invalid request : %s" % str_query)
            break
        
        # reset retry since last request is ok
        retry = retry_init
                
        #logger.debug("totalResults : %s" % root.find(".//totalResults").text )
        logger.debug("%s" % root.find(".//subtitle").text )
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
                    try:
                        safe[date_entry.attrib['name']]=datetime.datetime.strptime(date_entry.text,dateformat)
                    except ValueError:
                        safe[date_entry.attrib['name']]=datetime.datetime.strptime(date_entry.text[0:19],dateformat_alt)
                    
                for link in entry.findall("link"):
                    url_name='url'
                    if 'rel' in link.attrib:
                        url_name="%s_%s" % (url_name, link.attrib['rel'])
                    safe[url_name]=link.attrib['href']


                # convert fooprint to wkt
                safe['footprint'] = wkt.loads(safe['footprint'])
                
                
                # append to safes
                safes=safes.append(safe, ignore_index=True)
                start+=1
            # sort by sensing date
            safes=safes.sort_values('beginposition')
            safes.reset_index(drop=True,inplace=True)
    
    return safes
    
    
def colocalize(safes, gdf):
    """colocalize safes and gdf"""
    safes_coloc = safes.iloc[0:0,:].copy()
    
    for gdf_index , gdf_item in gdf.iterrows():
        begindate=gdf_item.beginposition 
        enddate=gdf_item.endposition
        # time coloc
        for safe_index , safe in safes.iterrows():
            # check for time range overlap
            latest_start = max(safe.beginposition , begindate)
            earliest_end = min(safe.endposition , enddate)
            overlap = (earliest_end - latest_start)
            
            if overlap >= datetime.timedelta(0) : 
                # intersection coloc
                if getattr(safe,safes.geometry.name).intersects(getattr(gdf_item,gdf.geometry.name)):
                    colocated = safes.loc[[safe_index]]  # one row df
                    # set same index as rom from gdf by adding temp col
                    colocated['__rowindex'] = gdf_index
                    colocated.set_index('__rowindex',drop=True,inplace=True)
                    colocated.rename_axis(gdf.index.name,inplace=True)
                    if colocated.iloc[0]['filename'] in safes_coloc['filename']:
                        logger.debug('here')
                        pass
                    safes_coloc = safes_coloc.append(colocated)
        
    
    return safes_coloc

def remove_duplicates(safes_ori,keep_list=[]):
    """
    Remove duplicate safe (ie same footprint with same date, but different prodid)
    """
    safes=safes_ori.copy()
    if not safes.empty:
        # remove duplicate safes
        
        # add a temporary col with filename radic
        safes['__filename_radic'] = [f[0:62] for f in safes['filename']]
        
        uniques_radic=safes['__filename_radic'].unique() 
        
        for filename_radic in uniques_radic:
            sames_safes=safes[safes['__filename_radic'] == filename_radic]
            if len(sames_safes['filename'].unique()) > 1:
                logger.debug("prodid count > 1: %s" % ([s for s in sames_safes['filename'].unique()]))
                force_keep=list(set(sames_safes['filename']).intersection(keep_list))
                to_keep = sames_safes['ingestiondate'].max()  #warning : may induce late reprocessing (ODL link) . min() is safer, but not the best quality
                
                if force_keep:
                    _to_keep=sames_safes[sames_safes['filename'] == force_keep[0]]['ingestiondate'].iloc[0]
                    if _to_keep != to_keep:
                        logger.warning('remove_duplicate : force keep safe %s' % force_keep[0])
                        to_keep = _to_keep
                logger.debug("only keep : %s " % [ f for f in safes[safes['ingestiondate'] == to_keep]['filename'] ])
                safes = safes[ (safes['ingestiondate'] == to_keep ) | (safes['__filename_radic'] != filename_radic)]
                
                
        safes.drop('__filename_radic',axis=1,inplace=True)
    return safes

def get_datatakes(safes, datatake=0, user='guest', password='guest', cachedir=None):
    safes['datatake_index'] = 0
    for safe in list(safes['filename']):
        safe_index = safes[safes['filename'] == safe].index[0]
        takeid=safe.split('_')[-2]
        safe_rad="_".join(safe.split('_')[0:4])
        safes_datatake=scihubQuery_raw('filename:%s_*_*_*_%s_*' % (safe_rad, takeid),user=user,password=password,cachedir=cachedir)
        #FIXME duplicate are removed, even if duplicate=True 
        safes_datatake = remove_duplicates(safes_datatake,keep_list=[safe])
        
        try:
            ifather = safes_datatake[safes_datatake['filename'] == safe].index[0]
        except:
            logger.warn('Father safe was not the most recent one (scihub bug ?)')
        
        
        #ifather=safes_datatake.index.get_loc(father) # convert index to iloc
        
        safes_datatake['datatake_index'] = safes_datatake.index - ifather
        
        
        # get adjacent safes
        safes_datatake = safes_datatake[abs(safes_datatake['datatake_index']) <= datatake]
        
        # set same index as father safe
        safes_datatake.set_index(gpd.GeoSeries([safe_index] * len(safes_datatake)),inplace=True)
        
        # remove datatake allready in safes (ie father and allready colocated )
        for safe_datatake in safes_datatake['filename']:
            if (safes['filename'] == safe_datatake).any():
                #FIXME take the lowest abs(datatake_index)
                safes_datatake=safes_datatake[safes_datatake['filename'] != safe_datatake]
        
        
        safes = safes.append(safes_datatake)
    return safes
    
def normalize_gdf(gdf,startdate=None,stopdate=None,date=None,dtime=None,timedelta_slice=datetime.timedelta(weeks=1)):
    """ return a normalized gdf list 
    start/stop date name will be 'beginposition' and 'endposition'
    """
    norm_gdf=gdf.copy()
    gdf_slices = []
    
    if date in norm_gdf:
        if (startdate not in norm_gdf) and (stopdate not in norm_gdf):
            norm_gdf['beginposition'] = norm_gdf[date] - dtime
            norm_gdf['endposition'] = norm_gdf[date] + dtime
        else:
            raise ValueError('date keyword conflict with startdate/stopdate')
    
    if (startdate in norm_gdf) and (startdate != 'beginposition'):
        norm_gdf['beginposition'] = norm_gdf[startdate]
        
    if (stopdate in norm_gdf) and (stopdate != 'endposition'):
        norm_gdf['endposition'] = norm_gdf[stopdate]
        
        
    # slice
    if timedelta_slice is not None:
        mindate=norm_gdf['beginposition'].min()
        maxdate=norm_gdf['endposition'].max()
        slice_begin = mindate
        slice_end = slice_begin
        while slice_end <= maxdate:
            slice_end = slice_begin + timedelta_slice
            gdf_slice=norm_gdf[ (norm_gdf['beginposition'] >= slice_begin ) & (norm_gdf['endposition'] <= slice_end) ]
            if gdf_slice.empty:   
                # not slicing, but expanding.
                gdf_slice=gdf.copy()
                gdf_slice['beginposition'] = slice_begin
                gdf_slice['endposition'] = min(slice_end,maxdate)
            gdf_slices.append(gdf_slice)
            slice_begin = slice_end
    else:
        gdf_slices = norm_gdf 
    
    return gdf_slices

def scihubQuery_new(gdf=None,startdate=None,stopdate=None,date=None,dtime=None,timedelta_slice=datetime.timedelta(weeks=1),filename='S1*', datatake=0, duplicate=False, query=None, user='guest', password='guest', min_sea_percent=None, show=False, cachedir=None, cacherefreshrecent=datetime.timedelta(days=7)):
    """
    
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
    return :
        a geodataframe with safes from scihub, colocated with input gdf (ie same index)
    """
    
    gdflist= normalize_gdf(gdf,startdate=startdate,stopdate=stopdate,date=date,dtime=dtime,timedelta_slice=timedelta_slice)
    safes_list = []  # final request
    safes_unfiltered_list = [] # raw request
    safes_sea_ok_list = []
    safes_sea_nok_list = []
    
    # decide if loop is over dataframe or over rows
    if isinstance(gdflist, list):
        iter_gdf = gdflist
    else:
        iter_gdf = gdflist.itertuples()
    
    for gdf_slice in iter_gdf:
        if isinstance(gdf_slice, tuple):
            gdf_slice=gpd.GeoDataFrame([gdf_slice],index=[gdf_slice.Index]) #.reindex_like(gdf) # only one row
            
        if gdf_slice.empty:
            continue
    
        q=[]
        footprint=""
        datePosition=""
        dateage = datetime.timedelta(weeks=100000) # old date age  per default too allow caching if no dates provided
            
            
        # get min/max date
        mindate = gdf_slice['beginposition'].min()
        maxdate = gdf_slice['endposition'].max()
        dateage=(datetime.datetime.utcnow() - maxdate) # used for cache age
        
        if dateage < cacherefreshrecent:
            logger.debug("recent request. disabling cache")
            _cachedir = None
        else:
            _cachedir = cachedir
                
        datePosition="beginPosition:[%s TO %s]" % (mindate.strftime(dateformat) , maxdate.strftime(dateformat) ) # shorter request . endPosition is just few seconds in future
        q.append(datePosition)
            
        q.append("filename:%s" % filename)
        
        if query:
            q.append("(%s)" % query)
        
        # get geometry enveloppe
        if timedelta_slice is not None:
            from shapely.geometry.collection import GeometryCollection
            shape = GeometryCollection(list(gdf_slice.geometry))
            shape = shape.buffer(2.0)
            shape = shape.simplify(1.5)        
        else:
            shape = ops.cascaded_union(gdf_slice.geometry) # will return the unique geometry of the unique ow
        #round the shape
        shape=wkt.loads(wkt.dumps(shape,rounding_precision=rounding_precision))    
        shape=split_boundaries(shape)
        wkt_shape=wkt.dumps(shape,rounding_precision=rounding_precision)
        
        footprint='(footprint:\"Intersects(%s)\" )' % wkt_shape
        q.append(footprint)
        
        
        str_query = ' AND '.join(q)
        
        logger.debug("query: %s" % str_query)
        
        safes_unfiltered=scihubQuery_raw(str_query, user=user, password=password, cachedir=_cachedir)
        
        safes=colocalize(safes_unfiltered, gdf_slice)
        
        if duplicate:
            safes = remove_duplicates(safes)
        
            
        # datatake collection to be done after colocalisation
        if datatake != 0:
            logger.debug("Asking for same datatakes")
            safes = get_datatakes(safes, datatake=datatake, user=user,password=password,cachedir=_cachedir)
                
        if not duplicate:
            safes = remove_duplicates(safes)
        
        if min_sea_percent is not None:
               safes_sea_percent = (safes.area - safes.intersection(earth).area ) / safes.area * 100
               safes_sea_ok = safes[safes_sea_percent >= min_sea_percent ]
               safes_sea_nok = safes[safes_sea_percent < min_sea_percent ]
               safes = safes_sea_ok
               
        # sort by sensing date  
        safes=safes.sort_values('beginposition')
        logger.info("from %s to %s : %s SAFES" % (mindate , maxdate, len(safes)))

        safes_list.append(safes)
        safes_unfiltered_list.append(safes_unfiltered)
        if min_sea_percent is not None:
            safes_sea_ok_list.append(safes_sea_ok)
            safes_sea_nok_list.append(safes_sea_nok)
        
    safes = pd.concat(safes_list,sort=False)
    safes = safes.sort_values('beginposition')
    safes_unfiltered = pd.concat(safes_unfiltered_list,sort=False)
    if min_sea_percent is not None:
        safes_sea_ok = pd.concat(safes_sea_ok_list,sort=False)
        safes_sea_nok = pd.concat(safes_sea_nok_list,sort=False)
    
    if show:
        import matplotlib.pyplot as plt
        import matplotlib as mpl
        fig, ax = plt.subplots(figsize=(10,7))
        handles = []
        gdf_slice.plot(ax=ax, color='none' , edgecolor='green',zorder=3)
        handles.append(mpl.lines.Line2D([], [], color='green', label='user request'))
        if shape is not None:
            gdf_sel=gpd.GeoDataFrame({'geometry':[shape]})
            gdf_sel.plot(ax=ax,color='none',edgecolor='red',zorder=3)
            handles.append(mpl.lines.Line2D([], [], color='red', label='scihub request'))
            
        safes_unfiltered.plot(ax=ax,color='none' , edgecolor='orange',zorder=1, alpha=0.2)
        handles.append(mpl.lines.Line2D([], [], color='orange', label='not colocated'))
        if len(safes) > 0:
            safes.plot(ax=ax,color='none' , edgecolor='blue',zorder=2, alpha=0.2)
            handles.append(mpl.lines.Line2D([], [], color='blue', label='colocated'))
            try:
                safes[safes['datatake_index'] != 0].plot(ax=ax,color='none' , edgecolor='cyan',zorder=2,alpha=0.2)
                handles.append(mpl.lines.Line2D([], [], color='cyan', label='datatake'))
            except:
                pass # no datatake
            if min_sea_percent is not None:
                safes_sea_nok.plot(ax=ax,color='none',edgecolor='olive',zorder=1,alpha=0.2)
                handles.append(mpl.lines.Line2D([], [], color='olive', label='sea area < %s %%' % min_sea_percent))
        continents = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
        continents.plot(ax=ax,zorder=0)
        #bounds = shape.buffer(5).bounds
        bounds = safes_unfiltered.unary_union.bounds
        ax.set_ylim([max(-90,bounds[1]),min(90,bounds[3])])
        ax.set_xlim([max(-180,bounds[0]),min(180,bounds[2])])
                    
        plt.tight_layout()
        box = ax.get_position()
        ax.set_position([box.x0, box.y0 , box.width , box.height * 0.8])
        
        ax.legend(handles=handles,loc='lower center', bbox_to_anchor=(0.5, 1.05),ncol=5)
        plt.show()    
    
    return safes    

def scihubQuery(date=None,dtime=datetime.timedelta(hours=3) ,lonlat=None, ddeg=0.0 ,filename='S1*', datatake=False, duplicate=False, query=None, user='guest', password='guest', show=False, cachedir=None, cacherefreshrecent=datetime.timedelta(days=7)):
    """
    query='(platformname:Sentinel-1 AND sensoroperationalmode:WV)' 
    input:
        date: [ start, stop ] 
        if [ date ], dtime will be used to compute start and stop
        lonlat : ( lon, lat ) or [(lon1,lat1),(lon2,lat2),...] or shapely object
        duplicate : if True, will return safes with same prodid
        ddeg : float rounding precision in deg
        cachedir : cache requests for speed up
        cacherefreshrecent : timedelta from now. if requested date is recent, will refresh the cache to let scihub ingest new data
        
    """
    logger.warning("Deprecated. Use scihubQuery_new")
    q=[]
    dateformat="%Y-%m-%dT%H:%M:%S.%fZ"
    dateformat_alt="%Y-%m-%dT%H:%M:%S"
    footprint=""
    datePosition=""
    dateage = datetime.timedelta(weeks=100000) # old date age  per default too allow caching if no dates provided
        
    if date:
        try:
            len(date)
        except:
            date=[date]
        if len(date) == 2:
            startdate=date[0].strftime(dateformat)
            stopdate=date[1].strftime(dateformat)
            dateage=(datetime.datetime.utcnow() - date[1])
        else:
            startdate=(date[0]-dtime).strftime(dateformat)
            stopdate=(date[0]+dtime).strftime(dateformat)
            dateage=(datetime.datetime.utcnow() - date[0])
            
        #datePosition="(beginPosition:[%s TO %s] OR endPosition:[%s TO %s])" % (startdate , stopdate , startdate, stopdate)
        datePosition="beginPosition:[%s TO %s]" % (startdate , stopdate ) # shorter request . endPosition is just few seconds in future
        q.append(datePosition)
        
    q.append("filename:%s" % filename)
    
    if query:
        q.append("(%s)" % query)
    
    if lonlat:
        if not hasattr(lonlat,'to_wkt'):
            from shapely.geometry import Polygon,Point
            try:
                shape=Polygon(lonlat)
            except (TypeError,ValueError):
                shape=Point(lonlat)
        else:
            shape=lonlat
        # disable simplification (up to the caller to do so)
        #else:
        #    shape=lonlat.exterior.convex_hull.simplify(0.1, preserve_topology=False)
        
        if ddeg > 0.0:
            shape=shape.buffer(ddeg,resolution=2)
            
        #round the shape
        
        shape=wkt.loads(wkt.dumps(shape,rounding_precision=rounding_precision))    
            
        shape=split_boundaries(shape)
        
       
        wkt_shape=wkt.dumps(shape,rounding_precision=rounding_precision)
        
        footprint='(footprint:\"Intersects(%s)\" )' % wkt_shape
        q.append(footprint)
    
    
    str_query = ' AND '.join(q)
    
    logger.debug("query: %s" % str_query)
    
    safes={}
    start=0
    count=1 # arbitrary count > start
    while start < count:
        params=OrderedDict([("start" ,start ), ("rows", 100), ("q",str_query)])
        root=None
        cachefile=None
        if cachedir is not None:
            md5request=hashlib.md5(("%s" % params).encode('utf-8')).hexdigest()
            cachefile=os.path.join(cachedir,md5request)
            if os.path.exists(cachefile):
                if dateage > cacherefreshrecent:
                    logger.debug("reading from cachefile %s" % cachefile)
                    try:
                        with open(cachefile, 'a'):
                            os.utime(cachefile, None)
                    except Exception as e:
                        logger.warning('unable to touch %s : %s' % (cachefile , str(e) ) )
                        
                    try:
                        root = remove_dom(etree.parse(cachefile))
                    except:
                        logger.warning('removing invalid cachefile %s' % cachefile)
                        os.unlink(cachefile)
                        root=None
                else:
                    logger.info('too recent request (%s). Ignoring cachefile %s' % (dateage,cachefile))
        
        if root is None:
            # request not cached
            xmlout=requests.get(urlapi,auth=(user,password),params=params)
        
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
                raise ValueError('scihub query error')
            
            if cachefile is not None:
                try:
                    with open(cachefile,'wb') as f:
                        f.write(etree.tostring(root, pretty_print=True))
                except:
                    logger.warning('unable to write cachefile %s' % cachefile)
                
            
        
        #<opensearch:totalResults>442</opensearch:totalResults>\n
        try:
            count=int(root.find(".//totalResults").text)
        except:
            # there was an error in request
            if cachefile is not None:
                os.unlink(cachefile)
            
            logger.critical("invalid request : %s" % str_query)
            break
            
                
        #logger.debug("totalResults : %s" % root.find(".//totalResults").text )
        logger.debug("%s" % root.find(".//subtitle").text )
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
                    try:
                        safe[date_entry.attrib['name']]=datetime.datetime.strptime(date_entry.text,dateformat)
                    except ValueError:
                        safe[date_entry.attrib['name']]=datetime.datetime.strptime(date_entry.text[0:19],dateformat_alt)
                    
                for link in entry.findall("link"):
                    url_name='url'
                    if 'rel' in link.attrib:
                        url_name="%s_%s" % (url_name, link.attrib['rel'])
                    safe[url_name]=link.attrib['href']
                #safes["%s" % filename] = safe
                
                # append to safes
                if not safes:
                    safes=safe.copy()
                    for field in safes:
                        safes[field]=[safes[field]]
                else:
                    for field in safes:
                        if field not in safe:
                            val=None
                        else:
                            val=safe[field]
                        safes[field].append(val)
                
                start+=1
        #else:
        #    start=-1
        
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
    if safes and not duplicate:
        # remove duplicate safes
        filenames=safes['filename']
        filenames_radic=[f[0:62] for f in filenames]
        toremove_ind=[] # index list to delete
        for filename_radic in filenames_radic:
            if filenames_radic.count(filename_radic) > 1:
                dup_ind=[i for i,val in enumerate(filenames_radic) if val==filename_radic]
                for i in dup_ind:
                    logger.debug("duplicate prodid : %s" % (safes['filename'][i]))
                
                # keep fist ingested SAFE
                keep_ind=safes['ingestiondate'].index(min([ safes['ingestiondate'][i] for i in dup_ind ]))
                del_ind=list(dup_ind)
                del_ind.remove(keep_ind)
                toremove_ind=toremove_ind+del_ind
        for f in safes.keys():
            for d in reversed(list(set(toremove_ind))):
                del safes[f][d]
                
    if not safes:
        logger.debug("No results from scihub. Will return empty.")
        
    safes=pd.DataFrame(safes)
    if 'footprint' in safes:
        safes['footprint'] = safes['footprint'].apply(wkt.loads)
        safes=gpd.GeoDataFrame(safes,geometry='footprint')
    else:
        safes=gpd.GeoDataFrame(safes)
        
    if show:
        import matplotlib.pyplot as plt
        
        map = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres')).plot(color='white', edgecolor='black')
        
        if lonlat is not None:
            gdf_sel=gpd.GeoDataFrame({'geometry':[shape]})
            map = gdf_sel.plot(ax=map,color='red',alpha=0.3)
        
        if len(safes) > 0:
            safes.plot(ax=map,color='blue')
        plt.show()
        

    return safes


       

