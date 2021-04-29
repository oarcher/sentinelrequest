import datetime
import pandas as pd
import geopandas as gpd
import numpy as np
import sys
from tqdm.auto import tqdm
import time

import logging
from builtins import isinstance
logging.basicConfig()
logger = logging.getLogger('geopandas_coloc')
logger.setLevel(logging.INFO)

if sys.gettrace():
    logger.setLevel(logging.DEBUG)


def colocalize_apply(gdf1, gdf2, progress=False):
    """colocalize gdf1 and gdf2
    
    return:
      2 pandas Index idx1 and idx2, of the same size. idx1 are colocated index from gdf1 that colocalize with idx2 from gdf2
      (note that index may not be unique if some are colocated more than once. 
    """
    if not sys.stderr.isatty() and "tqdm.std" in  str(tqdm):
        progress = False
    def row_coloc(gdf_item,gdf2,gdf_geometry_name='geometry'):
        timeok_gdf2 = gdf2[gdf2_date_interval.overlaps(gdf_item.date_interval__)]
            
        if hasattr(gdf_item,gdf1_geometry_name) and hasattr(gdf2,'geometry'):
            intersect_gdf2_ok = timeok_gdf2.contains(getattr(gdf_item,gdf1_geometry_name)) |  timeok_gdf2.intersects(getattr(gdf_item,gdf1_geometry_name)) | timeok_gdf2.geometry.within(getattr(gdf_item,gdf1_geometry_name))
        else:
            # if the user gave no geometry : all index
            intersect_gdf2_ok = slice(None)
            
        intersect_gdf2_idx = timeok_gdf2[intersect_gdf2_ok].index
        return timeok_gdf2[intersect_gdf2_ok].index
     
     
    if not 'date_interval__' in gdf1:
        gdf1['date_interval__'] =  pd.IntervalIndex.from_arrays(gdf1['startdate'],gdf1['stopdate'])
    else:
        drop1=False
    if 'date_interval__' in gdf2:
        gdf2_date_interval = pd.IntervalIndex(gdf2['date_interval__'])
    else:
        gdf2_date_interval = pd.IntervalIndex.from_arrays(gdf2['startdate'],gdf2['stopdate'])
 
        
    gdf1_geometry_name = gdf1.geometry.name
    gdf2_geometry_name = gdf2.geometry.name
    
    # empty index to store colocalization results
    idx1=gdf1.index.delete(slice(None))
    idx2=gdf2.index.delete(slice(None))
    
    if isinstance(gdf1.index,pd.MultiIndex):
        indexer1 = pd.MultiIndex.from_tuples
    else:
        indexer1 = pd.Index
    
    tqdm.pandas(disable = not progress, leave=False)
    gdf2_coloc_idx = gdf1.progress_apply(lambda row : row_coloc(row, gdf2,gdf_geometry_name=gdf1.geometry.name),axis=1)
    for gdf1_idx , gdf2_idx_serie in gdf2_coloc_idx.items():
        for gdf2_idx in  gdf2_idx_serie:
            idx1 = idx1.append(indexer1([gdf1_idx]))
            idx2 = idx2.append(indexer1([gdf2_idx]))
    return idx1,idx2

def colocalize_loop(gdf1, gdf2, progress=False):
    """colocalize gdf1 and gdf2
    
    return:
      2 pandas Index idx1 and idx2, of the same size. idx1 are colocated index from gdf1 that colocalize with idx2 from gdf2
      (note that index may not be unique if some are colocated more than once. 
    """
    if not sys.stderr.isatty() and "tqdm.std" in  str(tqdm):
        progress = False
    if len(gdf1) > len(gdf2):
        idx2,idx1 = colocalize_loop(gdf2, gdf1, progress=progress)
        return idx1,idx2
    drop1=True
    if not 'date_interval__' in gdf1:
        gdf1['date_interval__'] =  pd.IntervalIndex.from_arrays(gdf1['startdate'],gdf1['stopdate'])
    else:
        drop1=False
    if 'date_interval__' in gdf2:
        gdf2_date_interval = pd.IntervalIndex(gdf2['date_interval__'])
    else:
        gdf2_date_interval = pd.IntervalIndex.from_arrays(gdf2['startdate'],gdf2['stopdate'])
            
    gdf1_geometry_name = gdf1.geometry.name
    gdf2_geometry_name = gdf2.geometry.name
    
    # empty index to store colocalization results
    idx1=gdf1.index.delete(slice(None))
    idx2=gdf2.index.delete(slice(None))
    
    if isinstance(gdf1.index,pd.MultiIndex):
        indexer1 = pd.MultiIndex.from_tuples
    else:
        indexer1 = pd.Index
    
    # a for loop is faster than an apply loop
    for gdf_item in tqdm(gdf1.itertuples(),total=len(gdf1),disable = not progress,leave=False):
        timeok_gdf2 = gdf2[gdf2_date_interval.overlaps(gdf_item.date_interval__)]
            
        if hasattr(gdf_item,gdf1_geometry_name) and hasattr(gdf2,'geometry'):
            intersect_gdf2_ok = timeok_gdf2.contains(getattr(gdf_item,gdf1_geometry_name)) |  timeok_gdf2.intersects(getattr(gdf_item,gdf1_geometry_name)) | timeok_gdf2.geometry.within(getattr(gdf_item,gdf1_geometry_name))
        else:
            # if the user gave no geometry : all index
            intersect_gdf2_ok = slice(None)
            
        intersect_gdf2_idx = timeok_gdf2[intersect_gdf2_ok].index
        
        if intersect_gdf2_idx.size != 0:
            # idx1 must have same size as idx2. duplicate gdf_item.Index as needed
            idx1 = idx1.append(indexer1([gdf_item.Index] * len(intersect_gdf2_idx)))
            idx2 = idx2.append(intersect_gdf2_idx)
    
    if drop1:
        # remove column if it was not present
        gdf1.drop(columns=['date_interval__'],inplace=True)    
    return idx1,idx2   

def remove_overlaps(gdf):
    """ remove overlaps """
    t = time.time()
    gdf['next_date_interval__'] = gdf['date_interval__'].shift(fill_value=pd.Interval(pd.Timestamp(0),pd.Timestamp(0)))
    overlaps = gdf[['date_interval__','next_date_interval__']].apply(lambda x : x.date_interval__.overlaps(x.next_date_interval__),axis=1)
    gdf.drop(columns=['next_date_interval__'],inplace=True)
    if pd.IntervalIndex(gdf[~overlaps]['date_interval__']).is_overlapping:
        raise RuntimeError('still overlapping. need to implement loop')
    logger.debug('remove_overlaps done in %.1fs' % (time.time()-t))
    return gdf[~overlaps] , gdf[overlaps]

def _normalise_iter(gdf):
    _gdf = gdf.copy() 
    if 'date_interval__' not in _gdf: 
        _gdf = _gdf[['startdate','stopdate',_gdf.geometry.name]]
        _gdf.rename(columns={_gdf.geometry.name: "geometry"},inplace=True)
        _gdf.set_geometry('geometry',inplace=True)
        _gdf['date_interval__'] = pd.IntervalIndex.from_arrays(_gdf['startdate'],_gdf['stopdate'])
        _gdf.drop(columns=['startdate','stopdate'],inplace=True)
        # ensure sorted
        if not _gdf['date_interval__'].is_monotonic_increasing:
            _gdf.sort_values(['date_interval__'],inplace=True)
    return _gdf


def colocalize_iter(gdf1, gdf2, progress=False,_level=0):
    """
      2 pandas Index idx1 and idx2, of the same size. idx1 are colocated index from _gdf1 that colocalize with idx2 from _gdf2
      (note that index may not be unique if some are colocated more than once.
      
      This method is fast on very long non overlapping gdf, but can be very slow if there is
      some overlapping. A fallback to colocalize_loop is done in such cases. 
    """
    if not sys.stderr.isatty() and "tqdm.std" in  str(tqdm):
        progress = False
    t = time.time()
    
    _gdf1 = _normalise_iter(gdf1)
    _gdf2 = _normalise_iter(gdf2)
    
    _gdf1_is_overlapping = pd.IntervalIndex(_gdf1['date_interval__']).is_overlapping
    _gdf2_is_overlapping = pd.IntervalIndex(_gdf2['date_interval__']).is_overlapping
    logger.debug('gdf1 : %d , gdf2 : %d , level : %d. init in %.1fs' % (len(gdf1),len(gdf2),_level,time.time()-t))
    
    if _gdf1_is_overlapping and _gdf2_is_overlapping:
        logger.debug('both gdf are overlapping. Falling back to colocalize_loop')
        return colocalize_loop(gdf1, gdf2, progress=progress)
    
    # empty index to store colocalization results
    idx1=_gdf1.index.delete(slice(None))
    idx2=_gdf2.index.delete(slice(None))
     
    # check non overlaps
    if _gdf1_is_overlapping:
        _gdf1_no_overlaps, _gdf1_remain = remove_overlaps(_gdf1)
        overlapping1_rate = len(_gdf1_remain) / (len(_gdf1)) * 100
        if overlapping1_rate > 0:
            if overlapping1_rate < 10:
                logger.debug('gdf1 overlapping : %d%% of %d . using recursion %d with gdf2 len %d' % (overlapping1_rate,len(_gdf1),_level+1,len(_gdf2)))
                # we invert order of coloc to make gdf2 be checked first for overlaps
                idx2_rec,idx1_rec = colocalize_iter(_gdf2,_gdf1_remain,_level=_level+1)
            else:
                logger.debug('gdf1 overlapping : %d%% of %d . fallback to coloc_loop with gdf2 len %d' % (overlapping1_rate,len(_gdf1),len(_gdf2)))
                idx1_rec,idx2_rec = colocalize_loop(_gdf1_remain, _gdf2, progress=False)
            idx1 = idx1.append(idx1_rec)
            idx2 = idx2.append(idx2_rec)
            # continue with non overlapping
            _gdf1 = _gdf1_no_overlaps

    if _gdf2_is_overlapping:
        _gdf2_no_overlaps, _gdf2_remain = remove_overlaps(_gdf2)
        overlapping2_rate = len(_gdf2_remain) / (len(_gdf2)) * 100
        
        if overlapping2_rate > 0:
            if overlapping2_rate < 10:
                logger.debug('gdf2 overlapping : %d%% of %d . using recursion %d with gdf1 len %d' % (overlapping2_rate,len(_gdf2),_level+1,len(_gdf1)))
                idx2_rec,idx1_rec = colocalize_iter(_gdf2_remain,_gdf1,_level=_level+1)
            else:
                logger.debug('gdf2 overlapping : %d%% of %d . fallback to coloc_loop with gdf1 len %d' % (overlapping2_rate,len(_gdf2),len(_gdf1)))
                idx1_rec,idx2_rec = colocalize_loop(_gdf1, _gdf2_remain, progress=False)
            idx1 = idx1.append(idx1_rec)
            idx2 = idx2.append(idx2_rec)
            # continue with no overlaps
            _gdf2 = _gdf2_no_overlaps
    # get the way to add index    
    if isinstance(_gdf1.index,pd.MultiIndex):
        indexer1 = pd.MultiIndex.from_tuples
    else:
        indexer1 = pd.Index

    if isinstance(_gdf2.index,pd.MultiIndex):
        indexer2 = pd.MultiIndex.from_tuples
    else:
        indexer2 = pd.Index
    
    it1 = _gdf1.itertuples()
    it2 = _gdf2.itertuples()
    row1 = next(it1)
    row2 = next(it2)
    
    # compute total from progress bar from non overlaping interval
    if not _gdf1_is_overlapping:
        total = len(_gdf1)
    elif not _gdf2_is_overlapping:
        total = len(gdf2)
    else:
        progress = False
    with tqdm(total=total,disable=not progress) as pbar:
        while True:
            try:
                if row2.date_interval__.right < row1.date_interval__.left:
                    # no overlap. r2 before r1. advance it2
                    row2 = next(it2)
                    if not _gdf2_is_overlapping:
                        pbar.update(1)
                elif row1.date_interval__.right < row2.date_interval__.left:
                    # no overlap. r1 before r2. advance it1
                    row1 = next(it1)
                    if not _gdf1_is_overlapping:
                        pbar.update(1)
                else:
                    if row1.geometry.contains(row2.geometry) |  row1.geometry.intersects(row2.geometry) | row1.geometry.within(row2.geometry):
                        idx1 = idx1.append(indexer1([row1.Index]))
                        idx2 = idx2.append(indexer2([row2.Index]))
                    # determine whether to advance it1 or it2
                    if row1.date_interval__.right < row2.date_interval__.right:
                        # advance it1
                        row1 = next(it1)
                        if not _gdf1_is_overlapping:
                            pbar.update(1)
                    else:
                        # advance it2
                        row2 = next(it2)
                        if not _gdf2_is_overlapping:
                            pbar.update(1)
            except StopIteration:
                break
            
        pbar.update(total)
    return idx1,idx2

# default method
colocalize = colocalize_loop