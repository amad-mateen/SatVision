"""
Google Earth Engine data fetching services.
Handles optical (Sentinel-2), SAR (Sentinel-1), and Dynamic World baselines.
Production hardened to eliminate sub-tile grid cutting edge artifacts via spatial padding.
"""

import os
import math
import numpy as np
import tifffile as tiff
import requests
import ee
from src import config
import cv2


def download_gee_tile(image, n, s, e, w, prefix, r, c, scale=10):
    """
    Download a partitioned tile slice from Earth Engine as a localized GeoTIFF.
    """
    region = ee.Geometry.BBox(w, s, e, n)
    url = image.getDownloadURL({
        'crs': 'EPSG:4326',
        'region': region,
        'scale': scale,
        'format': 'GEO_TIFF'
    })
    
    try:
        resp = requests.get(url, timeout=config.GEE_REQUEST_TIMEOUT)
        if resp.status_code != 200:
            print(f"❌ Tile {r}-{c} failed with status {resp.status_code}.", flush=True)
            return None
        
        path = os.path.join(config.DOWNLOADS_DIR, f"{prefix}_tile_{r}_{c}.tiff")
        with open(path, 'wb') as f:
            f.write(resp.content)
        return path
    except Exception as e:
        print(f"❌ Tile download failed {r}-{c}: {e}", flush=True)
        return None


def stitch_tiles_safely(grid, is_3d=False):
    """
    Stitch a 2D list of image tiles using zero-padding instead of truncation.
    Eliminates geometric square-notch boundary artifacts completely.
    """
    # Step 1: Uniformly stitch columns inside each individual row block
    stitched_rows = []
    for r_idx, row_list in enumerate(grid):
        max_h = max(tile.shape[0] for tile in row_list)
        padded_row_tiles = []
        
        for tile in row_list:
            h, w = tile.shape[:2]
            if h < max_h:
                # Pad the bottom margin with zeros to maintain resolution grid alignment
                pad_bottom = max_h - h
                border_shape = (pad_bottom, w, tile.shape[2]) if is_3d else (pad_bottom, w)
                padding = np.zeros(border_shape, dtype=tile.dtype)
                tile = np.concatenate([tile, padding], axis=0)
            padded_row_tiles.append(tile)
            
        stitched_rows.append(np.concatenate(padded_row_tiles, axis=1))

    # Step 2: Uniformly vertical-stitch all rows together into the final matrix
    max_w = max(row.shape[1] for row in stitched_rows)
    padded_rows = []
    for row in stitched_rows:
        h, w = row.shape[:2]
        if w < max_w:
            # Pad the right margin with zeros to seamlessly join row transitions
            pad_right = max_w - w
            border_shape = (h, pad_right, row.shape[2]) if is_3d else (h, pad_right)
            padding = np.zeros(border_shape, dtype=row.dtype)
            row = np.concatenate([row, padding], axis=1)
        padded_rows.append(row)

    return np.concatenate(padded_rows, axis=0)


def fetch_optical_composite(coords, time_interval, filename_prefix, scale=10):
    """
    Fetch Sentinel-2 optical composite with cloud masking.
    Automatically segments massive regions dynamically using lossless padding alignment.
    """
    try:
        region = ee.Geometry.BBox(coords['west'], coords['south'], coords['east'], coords['north'])
        start_date, end_date = time_interval
        
        col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
               .filterBounds(region)
               .filterDate(start_date, end_date)
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', config.S2_CLOUD_THRESHOLD)))
        
        if col.size().getInfo() == 0:
            col = (ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
                   .filterBounds(region)
                   .filterDate(start_date, end_date)
                   .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', config.S2_CLOUD_THRESHOLD)))
            
            if col.size().getInfo() == 0:
                return None, None, None, 100.0
        
        def maskS2clouds(image):
            qa = image.select('QA60')
            cloudBitMask = 1 << 10
            cirrusBitMask = 1 << 11
            mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
            return image.updateMask(mask)
        
        mosaic = col.map(maskS2clouds).median()
        final_image = mosaic.select(config.S2_BANDS).toInt16().unmask(0)
        
        valid_mask = final_image.select('B4').gt(0)
        stats = valid_mask.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=config.GEE_SCALE_OPTICAL,
            maxPixels=1e9
        )
        clear_fraction = stats.get('B4').getInfo()
        if clear_fraction is None:
            clear_fraction = 0
        cloud_percent = (1.0 - clear_fraction) * 100.0
        
        if cloud_percent > config.OPTICAL_CLEAR_THRESHOLD:
            return None, None, None, cloud_percent
        
        actual_date = end_date
        source_type = "Sentinel-2 Optical (Cloud-Masked Composite)"
        
        n, s, e, w = coords['north'], coords['south'], coords['east'], coords['west']
        
        if scale == config.SCALE_XLARGE:
            max_deg_step = config.MAX_DEG_STEP_XLARGE
        elif scale == config.SCALE_LARGE:
            max_deg_step = config.MAX_DEG_STEP_LARGE
        else:
            max_deg_step = config.MAX_DEG_STEP_SMALL
            
        rows = math.ceil((n - s) / max_deg_step)
        cols = math.ceil((e - w) / max_deg_step)
        lat_steps = np.linspace(n, s, rows + 1)
        lon_steps = np.linspace(w, e, cols + 1)
        
        grid_data = []
        for r in range(rows):
            row_list = []
            for c in range(cols):
                tile_n, tile_s = lat_steps[r], lat_steps[r+1]
                tile_w, tile_e = lon_steps[c], lon_steps[c+1]
                tile_path = download_gee_tile(final_image, tile_n, tile_s, tile_e, tile_w,
                                             filename_prefix, r, c, scale=scale)
                if not tile_path:
                    return None, None, None, 100.0
                
                img = tiff.imread(tile_path)
                row_list.append(img)
                os.remove(tile_path)
            grid_data.append(row_list)
        
        # Safe Stitching Execution
        final_stitched = stitch_tiles_safely(grid_data, is_3d=True)
        
        save_path = os.path.join(config.DOWNLOADS_DIR, f"{filename_prefix}.tiff")
        tiff.imwrite(save_path, final_stitched)
        
        return save_path, actual_date, source_type, cloud_percent
    
    except Exception as e:
        print(f"❌ GEE Optical Error {filename_prefix}: {e}", flush=True)
        return None, None, None, 100.0


def fetch_sar_data(coords, time_interval, filename_prefix, is_baseline=False, scale=10):
    """
    Fetch Sentinel-1 SAR imagery matrix (VV backscatter polarization).
    """
    try:
        region = ee.Geometry.BBox(coords['west'], coords['south'], coords['east'], coords['north'])
        start_date, end_date = time_interval
        
        s1_col = (ee.ImageCollection('COPERNICUS/S1_GRD')
                  .filterBounds(region)
                  .filterDate(start_date, end_date)
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', config.S1_POLARIZATION))
                  .filter(ee.Filter.eq('instrumentMode', config.S1_INSTRUMENT_MODE)))
        
        if s1_col.size().getInfo() == 0:
            return None, None, None
        
        if is_baseline:
            s1_image = s1_col.median().select(config.S1_POLARIZATION).unmask(-99)
        else:
            s1_image = s1_col.mosaic().select(config.S1_POLARIZATION).unmask(-99)
        
        final_image = s1_image.toFloat()
        
        n, s, e, w = coords['north'], coords['south'], coords['east'], coords['west']
        
        if scale == config.SCALE_XLARGE:
            max_deg_step = config.MAX_DEG_STEP_XLARGE
        elif scale == config.SCALE_LARGE:
            max_deg_step = config.MAX_DEG_STEP_LARGE
        else:
            max_deg_step = config.MAX_DEG_STEP_SMALL
        
        rows = math.ceil((n - s) / max_deg_step)
        cols = math.ceil((e - w) / max_deg_step)
        lat_steps = np.linspace(n, s, rows + 1)
        lon_steps = np.linspace(w, e, cols + 1)
        
        grid_data = []
        for r in range(rows):
            row_list = []
            for c in range(cols):
                tile_n, tile_s = lat_steps[r], lat_steps[r+1]
                tile_w, tile_e = lon_steps[c], lon_steps[c+1]
                tile_path = download_gee_tile(final_image, tile_n, tile_s, tile_e, tile_w,
                                             filename_prefix, r, c, scale=scale)
                if not tile_path:
                    return None, None, None
                
                img = tiff.imread(tile_path)
                row_list.append(img)
                os.remove(tile_path)
            grid_data.append(row_list)
        
        final_stitched = stitch_tiles_safely(grid_data, is_3d=False)
        
        actual_date = end_date
        source_type = "Sentinel-1 SAR (VV Backscatter)" if not is_baseline else "Sentinel-1 SAR (Dry-Season Baseline)"
        
        save_path = os.path.join(config.DOWNLOADS_DIR, f"{filename_prefix}_sar.tiff")
        tiff.imwrite(save_path, final_stitched)
        
        return save_path, actual_date, source_type
    
    except Exception as e:
        print(f"❌ SAR Error {filename_prefix}: {e}", flush=True)
        return None, None, None


def fetch_dynamic_world_baseline(coords, time_interval, filename_prefix, scale=10):
    """
    Fetch Dynamic World land cover discrete classification mapping for historical baselines.
    """
    try:
        region = ee.Geometry.BBox(coords['west'], coords['south'], coords['east'], coords['north'])
        start_date, end_date = time_interval
        
        dw_col = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
                  .filterBounds(region)
                  .filterDate(start_date, end_date))
        
        if dw_col.size().getInfo() == 0:
            return None, None
        
        final_image = dw_col.select('label').mode().eq(config.DW_WATER_CLASS).unmask(0).multiply(255).toByte()
        
        n, s, e, w = coords['north'], coords['south'], coords['east'], coords['west']
        
        if scale == config.SCALE_XLARGE:
            max_deg_step = config.MAX_DEG_STEP_XLARGE
        elif scale == config.SCALE_LARGE:
            max_deg_step = config.MAX_DEG_STEP_LARGE
        else:
            max_deg_step = config.MAX_DEG_STEP_SMALL
            
        rows = math.ceil((n - s) / max_deg_step)
        cols = math.ceil((e - w) / max_deg_step)
        lat_steps = np.linspace(n, s, rows + 1)
        lon_steps = np.linspace(w, e, cols + 1)
        
        grid_data = []
        for r in range(rows):
            row_list = []
            for c in range(cols):
                tile_n, tile_s = lat_steps[r], lat_steps[r+1]
                tile_w, tile_e = lon_steps[c], lon_steps[c+1]
                tile_path = download_gee_tile(final_image, tile_n, tile_s, tile_e, tile_w,
                                             filename_prefix, r, c, scale=scale)
                if not tile_path:
                    return None, None
                
                img = tiff.imread(tile_path)
                row_list.append(img)
                os.remove(tile_path)
            grid_data.append(row_list)
        
        final_stitched = stitch_tiles_safely(grid_data, is_3d=False)
        
        save_path = os.path.join(config.DOWNLOADS_DIR, f"{filename_prefix}.tiff")
        tiff.imwrite(save_path, final_stitched)
        
        return save_path, "Dynamic Dry-Season Anchor (April-May)"
    
    except Exception as e:
        print(f"❌ Dynamic World Error {filename_prefix}: {e}", flush=True)
        return None, None