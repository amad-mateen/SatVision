"""
Model service for loading and running PyTorch Lightning inference.
Implements thread-safe model loading and prediction with torch.no_grad() optimization.
"""

import os
import torch
import pytorch_lightning as pl
import segmentation_models_pytorch as smp
import numpy as np
from src import config

# Global model instance
_model = None


class DynamicEvalModel(pl.LightningModule):
    """
    PyTorch Lightning model wrapper for U-Net++ segmentation.
    Used for water/cloud segmentation tasks.
    """
    
    def __init__(self, **kwargs):
        super().__init__()
        self.save_hyperparameters()
        self.model_params = kwargs.get('model_params', {
            'model_type': 'unetplusplus',
            'encoder_name': 'resnet34',
            'in_channels': 6,
            'out_classes': 2
        })
        self._build_model()

    def _build_model(self):
        """Build the U-Net++ segmentation model."""
        self.model = smp.UnetPlusPlus(
            encoder_name=self.model_params.get('encoder_name', 'resnet34'),
            encoder_weights=None,
            in_channels=self.model_params.get('in_channels', 6),
            classes=self.model_params.get('out_classes', 2),
            activation=None
        )

    def forward(self, x):
        return self.model(x)


def initialize_model():
    """
    Load the PyTorch Lightning model from checkpoint.
    Model is placed on the configured device (GPU/CPU) and set to eval mode.
    """
    global _model
    
    print("⏳ Loading model...", flush=True)
    
    if not os.path.exists(config.CHECKPOINT_PATH):
        print(f"❌ Model Checkpoint Not Found: {config.CHECKPOINT_PATH}", flush=True)
        _model = None
        return None
    
    try:
        _model = DynamicEvalModel.load_from_checkpoint(
            config.CHECKPOINT_PATH,
            strict=False
        )
        _model.to(config.DEVICE)
        _model.eval()
        print("✅ Model Loaded Successfully!", flush=True)
        return _model
    except Exception as e:
        print(f"❌ Model Load Failed: {e}", flush=True)
        _model = None
        return None


def get_model():
    """Retrieve the loaded model instance."""
    return _model


def predict_water_mask(tiff_path):
    """
    Run inference on a TIFF image to predict water and cloud masks.
    
    Args:
        tiff_path: Path to the input TIFF file (6-channel optical image)
    
    Returns:
        Clean water mask (numpy array, uint8) or None on failure
    """
    import tifffile as tiff
    import cv2
    from src.services.cv2 import (
        apply_hanning_window, apply_cloud_detection,
        apply_water_detection, apply_morphological_cleanup,
        filter_small_contours
    )
    
    if _model is None or not os.path.exists(tiff_path):
        return None
    
    # Load and prepare image
    image = tiff.imread(tiff_path).astype(np.float32)
    
    if image.ndim == 3 and image.shape[2] == 6:
        image_tensor = np.transpose(image, (2, 0, 1))
    else:
        image_tensor = image.copy()
    
    # Normalize to [0, 1]
    scaled_tensor = np.clip(image_tensor / config.OPTICAL_NORMALIZATION_FACTOR, 0, 1)
    
    # Tiling parameters
    tile_size = config.TILE_SIZE
    overlap_ratio = config.TILE_OVERLAP_RATIO
    stride = int(tile_size * (1 - overlap_ratio))
    c, h, w = scaled_tensor.shape
    
    # Padding for tile overlap
    pad_h = (tile_size - (h % stride)) % stride + (tile_size - stride) if h % stride != 0 else 0
    pad_w = (tile_size - (w % stride)) % stride + (tile_size - stride) if w % stride != 0 else 0
    image_padded = np.pad(scaled_tensor, ((0, 0), (0, pad_h), (0, pad_w)), mode='reflect')
    
    padded_h, padded_w = image_padded.shape[1], image_padded.shape[2]
    
    # Initialize output maps
    prob_map_cloud = np.zeros((padded_h, padded_w), dtype=np.float32)
    prob_map_water = np.zeros((padded_h, padded_w), dtype=np.float32)
    count_map = np.zeros((padded_h, padded_w), dtype=np.float32)
    
    # Generate tile coordinates
    y_steps = list(range(0, padded_h - tile_size + 1, stride))
    x_steps = list(range(0, padded_w - tile_size + 1, stride))
    
    # Hanning window for smooth blending
    window_1d = np.hanning(tile_size)
    window_2d = np.outer(window_1d, window_1d).astype(np.float32)
    
    # Process tiles in batches
    tiles_batch = []
    coords_batch = []
    
    with torch.no_grad():  # Disable gradients for inference
        for y in y_steps:
            for x in x_steps:
                tile = image_padded[:, y:y+tile_size, x:x+tile_size]
                tiles_batch.append(tile)
                coords_batch.append((x, y))
                
                # Process batch when full or at end
                if len(tiles_batch) == config.BATCH_SIZE or (y == y_steps[-1] and x == x_steps[-1]):
                    batch_tensor = torch.from_numpy(np.stack(tiles_batch)).to(config.DEVICE)
                    logits = _model(batch_tensor)
                    probs = torch.sigmoid(logits).cpu().numpy()
                    
                    # Accumulate predictions
                    for i, (bx, by) in enumerate(coords_batch):
                        prob_cloud = probs[i, 0, :, :] * window_2d
                        prob_water = probs[i, 1, :, :] * window_2d
                        
                        prob_map_cloud[by:by+tile_size, bx:bx+tile_size] += prob_cloud
                        prob_map_water[by:by+tile_size, bx:bx+tile_size] += prob_water
                        count_map[by:by+tile_size, bx:bx+tile_size] += window_2d
                    
                    tiles_batch = []
                    coords_batch = []
    
    # Normalize by count map
    final_cloud_prob = (prob_map_cloud / (count_map + 1e-7))[:h, :w]
    final_water_prob = (prob_map_water / (count_map + 1e-7))[:h, :w]
    
    # Extract optical bands for cloud/water detection
    b2 = scaled_tensor[0, :h, :w]
    b3 = scaled_tensor[1, :h, :w]
    b4 = scaled_tensor[2, :h, :w]
    b8 = scaled_tensor[3, :h, :w]
    
    # Calculate brightness and NDWI
    brightness = np.sqrt(b2**2 + b3**2 + b4**2)
    ndwi = (b3 - b8) / (b3 + b8 + 1e-5)
    
    # Apply cloud detection
    base_cloud_mask = ((final_cloud_prob > config.CLOUD_DETECTION_THRESHOLD) & 
                       (brightness > config.BRIGHTNESS_THRESHOLD)).astype(np.uint8)
    
    # Dilate cloud mask for shadow buffering
    cloud_buffer_kernel = np.ones(config.CLOUD_BUFFER_KERNEL_SIZE, np.uint8)
    cloud_and_shadow_mask = cv2.dilate(base_cloud_mask, cloud_buffer_kernel, iterations=1)
    
    # Apply water detection
    raw_water_mask = (final_water_prob > config.NDWI_WATER_THRESHOLD) | (ndwi > config.NDWI_CLOUD_THRESHOLD)
    water_mask = raw_water_mask & (cloud_and_shadow_mask == 0) & (ndwi > config.NDWI_MIN_THRESHOLD)
    clean_mask = water_mask.astype(np.uint8)
    
    # Morphological cleanup
    clean_mask = apply_morphological_cleanup(clean_mask)
    
    # Remove small contours
    clean_mask = filter_small_contours(clean_mask)
    
    return clean_mask * 255