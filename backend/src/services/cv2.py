"""
OpenCV-based image processing services.
Handles water mask prediction, SAR processing, RGB preview generation, and overlay creation.
"""

import os
import numpy as np
import cv2
import tifffile as tiff
from src import config


def apply_hanning_window(tile_size):
    """Generate a 2D Hanning window for smooth tile blending."""
    window_1d = np.hanning(tile_size)
    return np.outer(window_1d, window_1d).astype(np.float32)


def apply_cloud_detection(prob_cloud, brightness):
    """Detect cloud pixels based on probability and brightness."""
    return ((prob_cloud > config.CLOUD_DETECTION_THRESHOLD) &
            (brightness > config.BRIGHTNESS_THRESHOLD)).astype(np.uint8)


def apply_water_detection(prob_water, ndwi, cloud_mask):
    """Detect water pixels based on probability, NDWI, and cloud exclusion."""
    raw_water = (prob_water > config.NDWI_WATER_THRESHOLD) | (ndwi > config.NDWI_CLOUD_THRESHOLD)
    return raw_water & (cloud_mask == 0) & (ndwi > config.NDWI_MIN_THRESHOLD)


def apply_morphological_cleanup(mask):
    """Apply closing and opening operations to clean mask."""
    close_kernel = np.ones(config.CLOSE_KERNEL_SIZE, np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)
    
    open_kernel = np.ones(config.OPEN_KERNEL_SIZE, np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel)
    
    return mask


def filter_small_contours(mask):
    """Remove contours smaller than minimum area threshold."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < config.MIN_CONTOUR_AREA:
            cv2.drawContours(mask, [cnt], -1, 0, -1)
    
    return mask


def process_sar_image(tiff_path, preview_filename):
    """
    Process SAR image for water detection and visualization.
    """
    if not os.path.exists(tiff_path):
        return None, None
    
    try:
        sar_db = tiff.imread(tiff_path).astype(np.float32)
        
        water_min, water_max = config.SAR_WATER_DB_RANGE
        water_mask = ((sar_db < water_min) & (sar_db > water_max)).astype(np.uint8) * 255
        
        close_kernel = np.ones(config.CLOSE_KERNEL_SIZE, np.uint8)
        water_mask = cv2.morphologyEx(water_mask, cv2.MORPH_CLOSE, close_kernel)
        
        visual = np.clip((sar_db + config.SAR_DB_OFFSET) / config.SAR_DB_OFFSET, 0, 1) * 255
        visual = visual.astype(np.uint8)
        
        h, w = visual.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[:, :, 0] = visual  # B
        rgba[:, :, 1] = visual  # G
        rgba[:, :, 2] = visual  # R
        rgba[:, :, 3] = np.where(sar_db < -90, 0, 255)  # Transparency check for missing background data
        
        save_path = os.path.join(config.DOWNLOADS_DIR, preview_filename)
        cv2.imwrite(save_path, rgba)
        
        return water_mask, preview_filename
    
    except Exception as e:
        print(f"❌ SAR Processing Error {tiff_path}: {e}", flush=True)
        return None, None


def create_rgb_preview(tiff_path, filename):
    """
    Create an enhanced RGB preview from optical or water mask data.
    """
    if not os.path.exists(tiff_path):
        return None
    
    try:
        image = tiff.imread(tiff_path).astype(np.float32)
        
        if image.ndim == 2:
            rgb = np.zeros((image.shape[0], image.shape[1], 3), dtype=np.uint8)
            rgb[image == 255] = [255, 0, 0]
            save_path = os.path.join(config.DOWNLOADS_DIR, filename)
            cv2.imwrite(save_path, rgb)
            return filename
        
        if image.shape[0] == 6:
            image = np.transpose(image, (1, 2, 0))
        if np.max(image) > 1.0:
            image = image / config.OPTICAL_NORMALIZATION_FACTOR
        
        rgb = image[:, :, config.RGB_BAND_INDICES]
        rgb = np.clip(rgb * config.RGB_SCALING_FACTOR, 0, 1) * 255
        rgb = rgb.astype(np.uint8)
        
        gaussian = cv2.GaussianBlur(rgb, (0, 0), config.GAUSSIAN_BLUR_SIGMA)
        sharpened = cv2.addWeighted(
            rgb,
            config.GAUSSIAN_BLUR_SHARPEN_STRENGTH,
            gaussian,
            config.GAUSSIAN_BLUR_SUBTRACT_STRENGTH,
            0
        )
        
        save_path = os.path.join(config.DOWNLOADS_DIR, filename)
        cv2.imwrite(save_path, sharpened)
        return filename
    
    except Exception as e:
        print(f"❌ RGB Preview Error {tiff_path}: {e}", flush=True)
        return None


def create_overlay_png(mask, color, filename):
    """
    Create a semi-transparent PNG overlay from a binary mask.
    """
    if mask is None:
        return None
    
    try:
        h, w = mask.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        b, g, r = color
        
        rgba[mask == 255, 0] = b
        rgba[mask == 255, 1] = g
        rgba[mask == 255, 2] = r
        rgba[mask == 255, 3] = config.OVERLAY_ALPHA
        
        save_path = os.path.join(config.DOWNLOADS_DIR, filename)
        cv2.imwrite(save_path, rgba)
        return filename
    
    except Exception as e:
        print(f"❌ Overlay Error {filename}: {e}", flush=True)
        return None