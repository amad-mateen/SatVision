import os
import json
import numpy as np
import tifffile as tiff
import cv2
import torch
import pytorch_lightning as pl
import segmentation_models_pytorch as smp
import ee
import requests
from datetime import datetime, timedelta
from flask import Flask, request, Response, stream_with_context, send_from_directory
from flask_cors import CORS
import math
from google import genai
from google.genai import types
from PIL import Image
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import uuid
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

@app.route("/")
def health_check():
    return "✅ SatVision Backend is alive!", 200

# --- 1. CONFIGURATION & DATABASE ---
CHECKPOINT_PATH = "./models/SatVision_Model.ckpt"
DOWNLOADS_DIR = "server_downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MONGO_URI = os.environ.get("MONGO_URI")
try:
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client.satvision_db
    generations_col = db.generations
    print("✅ MongoDB Connected Successfully!", flush=True)
except Exception as e:
    print(f"❌ MongoDB Connection Failed: {e}", flush=True)
    db, generations_col = None, None

# --- 2. GOOGLE EARTH ENGINE SETUP ---
print("🌍 Initializing Earth Engine...", flush=True)
try:
    credentials_json = os.environ.get("EE_CREDENTIALS")
    if credentials_json:
        key_dict = json.loads(credentials_json)
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_info(
            key_dict,
            scopes=['https://www.googleapis.com/auth/earthengine']
        )
        ee.Initialize(credentials, project='gen-lang-client-0114614261')
        print("✅ Earth Engine Linked via Service Account.", flush=True)
    else:
        ee.Initialize(project='gen-lang-client-0114614261')
        print("✅ Earth Engine Linked via Local Auth.", flush=True)
except Exception as e:
    print(f"❌ Earth Engine Init Failed: {e}", flush=True)

# --- 3. MODEL DEFINITION ---
class DynamicEvalModel(pl.LightningModule):
    def __init__(self, **kwargs):
        super().__init__()
        self.save_hyperparameters()
        self.model_params = kwargs.get('model_params', {'model_type': 'unetplusplus', 'encoder_name': 'resnet34', 'in_channels': 6, 'out_classes': 2})
        self._build_model()

    def _build_model(self):
        self.model = smp.UnetPlusPlus(
            encoder_name=self.model_params.get('encoder_name', 'resnet34'),
            encoder_weights=None, 
            in_channels=self.model_params.get('in_channels', 6),
            classes=self.model_params.get('out_classes', 2),
            activation=None
        )

    def forward(self, x):
        return self.model(x)

print("⏳ Loading model...", flush=True)
try:
    model = DynamicEvalModel.load_from_checkpoint(CHECKPOINT_PATH, strict=False)
    model.to(DEVICE)
    model.eval()
    print("✅ Model Loaded Successfully!", flush=True)
except Exception as e:
    print(f"❌ Model Load Failed: {e}", flush=True)
    model = None

# --- 4. GEE FETCHING & UTILS ---

def download_gee_tile(image, n, s, e, w, prefix, r, c, scale=10):
    region = ee.Geometry.BBox(w, s, e, n)
    url = image.getDownloadURL({'crs': 'EPSG:4326', 'region': region, 'scale': scale, 'format': 'GEO_TIFF'})
    resp = requests.get(url, timeout=120)
    if resp.status_code != 200: 
        print(f"❌ Tile {r}-{c} failed.", flush=True)
        return None
        
    path = os.path.join(DOWNLOADS_DIR, f"{prefix}_tile_{r}_{c}.tiff")
    with open(path, 'wb') as f: 
        f.write(resp.content)
    return path

def fetch_optical_composite(coords, time_interval, filename_prefix):
    try:
        region = ee.Geometry.BBox(coords['west'], coords['south'], coords['east'], coords['north'])
        start_date, end_date = time_interval

        col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
               .filterBounds(region)
               .filterDate(start_date, end_date)
               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 35)))

        if col.size().getInfo() == 0: 
            col = (ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
                   .filterBounds(region)
                   .filterDate(start_date, end_date)
                   .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 35)))
            
            if col.size().getInfo() == 0:
                return None, None, None, 100.0 

        def maskS2clouds(image):
            qa = image.select('QA60')
            cloudBitMask = 1 << 10
            cirrusBitMask = 1 << 11
            mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0))
            return image.updateMask(mask)

        mosaic = col.map(maskS2clouds).median()
        s2_bands = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12']
        final_image = mosaic.select(s2_bands).toInt16().unmask(0)

        valid_mask = final_image.select('B4').gt(0)
        stats = valid_mask.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=100, 
            maxPixels=1e9
        )
        clear_fraction = stats.get('B4').getInfo()
        
        if clear_fraction is None: clear_fraction = 0
        cloud_percent = (1.0 - clear_fraction) * 100.0

        if cloud_percent > 85.0:
            return None, None, None, cloud_percent

        actual_date = end_date 
        source_type = "Sentinel-2 Optical (Cloud-Masked Composite)"

        n, s, e, w = coords['north'], coords['south'], coords['east'], coords['west']
        is_large = max(n - s, e - w) > 0.5
        MAX_DEG_STEP = 0.50 if is_large else 0.08
        current_scale = 50 if is_large else 10
        rows = math.ceil((n - s) / MAX_DEG_STEP)
        cols = math.ceil((e - w) / MAX_DEG_STEP)
        lat_steps = np.linspace(n, s, rows + 1)
        lon_steps = np.linspace(w, e, cols + 1)

        tile_arrays = []
        for r in range(rows):
            row_list = []
            for c in range(cols):
                tile_n, tile_s = lat_steps[r], lat_steps[r+1]
                tile_w, tile_e = lon_steps[c], lon_steps[c+1]
                tile_path = download_gee_tile(final_image, tile_n, tile_s, tile_e, tile_w, filename_prefix, r, c, scale=current_scale)
                if not tile_path: return None, None, None, 100.0
                img = tiff.imread(tile_path)
                row_list.append(img)
                os.remove(tile_path)
                
            min_h = min(tile.shape[0] for tile in row_list)
            row_list = [tile[:min_h, :, :] for tile in row_list]
            row_stitched = np.concatenate(row_list, axis=1)
            tile_arrays.append(row_stitched)

        min_w = min(row.shape[1] for row in tile_arrays)
        tile_arrays = [row[:, :min_w, :] for row in tile_arrays]
        final_stitched = np.concatenate(tile_arrays, axis=0)

        save_path = os.path.join(DOWNLOADS_DIR, f"{filename_prefix}.tiff")
        tiff.imwrite(save_path, final_stitched)
        
        return save_path, actual_date, source_type, cloud_percent

    except Exception as e:
        print(f"❌ GEE Optical Error {filename_prefix}: {e}", flush=True)
        return None, None, None, 100.0

def fetch_sar_data(coords, time_interval, filename_prefix, is_baseline=False):
    try:
        region = ee.Geometry.BBox(coords['west'], coords['south'], coords['east'], coords['north'])
        start_date, end_date = time_interval

        s1_col = (ee.ImageCollection('COPERNICUS/S1_GRD')
                  .filterBounds(region)
                  .filterDate(start_date, end_date)
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                  .filter(ee.Filter.eq('instrumentMode', 'IW')))

        if s1_col.size().getInfo() == 0: return None, None, None

        if is_baseline:
            s1_image = s1_col.median().select('VV').unmask(-99)
        else:
            s1_image = s1_col.mosaic().select('VV').unmask(-99)

        final_image = s1_image.toFloat()

        MAX_DEG_STEP = 0.08
        n, s, e, w = coords['north'], coords['south'], coords['east'], coords['west']
        rows = math.ceil((n - s) / MAX_DEG_STEP)
        cols = math.ceil((e - w) / MAX_DEG_STEP)
        lat_steps = np.linspace(n, s, rows + 1)
        lon_steps = np.linspace(w, e, cols + 1)

        tile_arrays = []
        for r in range(rows):
            row_list = []
            for c in range(cols):
                tile_n, tile_s = lat_steps[r], lat_steps[r+1]
                tile_w, tile_e = lon_steps[c], lon_steps[c+1]
                tile_path = download_gee_tile(final_image, tile_n, tile_s, tile_e, tile_w, filename_prefix, r, c, scale=current_scale)
                if not tile_path: return None, None, None
                img = tiff.imread(tile_path)
                row_list.append(img)
                os.remove(tile_path)
                
            min_h = min(tile.shape[0] for tile in row_list)
            row_list = [tile[:min_h, ...] for tile in row_list]
            row_stitched = np.concatenate(row_list, axis=1)
            tile_arrays.append(row_stitched)

        min_w = min(row.shape[1] for row in tile_arrays)
        tile_arrays = [row[:, :min_w, ...] for row in tile_arrays]
        final_stitched = np.concatenate(tile_arrays, axis=0)

        actual_date = end_date 
        source_type = "Sentinel-1 SAR (VV Backscatter)" if not is_baseline else "Sentinel-1 SAR (Dry-Season Baseline)"
        
        save_path = os.path.join(DOWNLOADS_DIR, f"{filename_prefix}_sar.tiff")
        tiff.imwrite(save_path, final_stitched)
        
        return save_path, actual_date, source_type

    except Exception as e:
        print(f"❌ SAR Error {filename_prefix}: {e}", flush=True)
        return None, None, None

def fetch_dynamic_world_baseline(coords, time_interval, filename_prefix):
    try:
        region = ee.Geometry.BBox(coords['west'], coords['south'], coords['east'], coords['north'])
        start_date, end_date = time_interval
        
        dw_col = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
                  .filterBounds(region)
                  .filterDate(start_date, end_date))
        
        if dw_col.size().getInfo() == 0: return None, None

        final_image = dw_col.select('label').mode().eq(0).unmask(0).multiply(255).toByte()

        MAX_DEG_STEP = 0.08
        n, s, e, w = coords['north'], coords['south'], coords['east'], coords['west']
        rows = math.ceil((n - s) / MAX_DEG_STEP)
        cols = math.ceil((e - w) / MAX_DEG_STEP)
        lat_steps = np.linspace(n, s, rows + 1)
        lon_steps = np.linspace(w, e, cols + 1)

        tile_arrays = []
        for r in range(rows):
            row_list = []
            for c in range(cols):
                tile_n, tile_s = lat_steps[r], lat_steps[r+1]
                tile_w, tile_e = lon_steps[c], lon_steps[c+1]
                tile_path = download_gee_tile(final_image, tile_n, tile_s, tile_e, tile_w, filename_prefix, r, c)
                if not tile_path: return None, None
                img = tiff.imread(tile_path)
                row_list.append(img)
                os.remove(tile_path)
                
            min_h = min(tile.shape[0] for tile in row_list)
            row_list = [tile[:min_h, ...] for tile in row_list]
            row_stitched = np.concatenate(row_list, axis=1)
            tile_arrays.append(row_stitched)

        min_w = min(row.shape[1] for row in tile_arrays)
        tile_arrays = [row[:, :min_w, ...] for row in tile_arrays]
        final_stitched = np.concatenate(tile_arrays, axis=0)
        
        save_path = os.path.join(DOWNLOADS_DIR, f"{filename_prefix}.tiff")
        tiff.imwrite(save_path, final_stitched)
        
        return save_path, "Dynamic Dry-Season Anchor (April-May)"

    except Exception as e:
        print(f"❌ Dynamic World Error {filename_prefix}: {e}", flush=True)
        return None, None

# --- 5. IMAGE PROCESSING UTILS ---

def predict_water_mask(tiff_path):
    if not model or not os.path.exists(tiff_path): return None

    image = tiff.imread(tiff_path).astype(np.float32)
    
    if image.ndim == 3 and image.shape[2] == 6:
        image_tensor = np.transpose(image, (2, 0, 1))
    else:
        image_tensor = image.copy()

    scaled_tensor = np.clip(image_tensor / 10000.0, 0, 1)

    tile_size, overlap = 256, 0.5
    stride = int(tile_size * (1 - overlap))
    c, h, w = scaled_tensor.shape
    
    pad_h = (tile_size - (h % stride)) % stride + (tile_size - stride) if h % stride != 0 else 0
    pad_w = (tile_size - (w % stride)) % stride + (tile_size - stride) if w % stride != 0 else 0
    image_padded = np.pad(scaled_tensor, ((0,0), (0, pad_h), (0, pad_w)), mode='reflect')
    
    padded_h, padded_w = image_padded.shape[1], image_padded.shape[2]
    
    prob_map_cloud = np.zeros((padded_h, padded_w), dtype=np.float32)
    prob_map_water = np.zeros((padded_h, padded_w), dtype=np.float32)
    count_map = np.zeros((padded_h, padded_w), dtype=np.float32)

    y_steps = list(range(0, padded_h - tile_size + 1, stride))
    x_steps = list(range(0, padded_w - tile_size + 1, stride))

    window_1d = np.hanning(tile_size)
    window_2d = np.outer(window_1d, window_1d).astype(np.float32)

    batch_size = 16  # Process 16 tiles simultaneously (adjust to 8 if you hit GPU memory limits)
    tiles_batch = []
    coords_batch = []

    with torch.no_grad():
        for y in y_steps:
            for x in x_steps:
                # 1. Extract the numpy tile and store it
                tile = image_padded[:, y:y+tile_size, x:x+tile_size]
                tiles_batch.append(tile)
                coords_batch.append((x, y))
                
                # 2. If we hit the batch size, OR we are on the very last patch, run inference
                if len(tiles_batch) == batch_size or (y == y_steps[-1] and x == x_steps[-1]):
                    # Stack list of arrays into a single (B, C, H, W) tensor
                    batch_tensor = torch.from_numpy(np.stack(tiles_batch)).to(DEVICE)
                    
                    # Forward pass
                    logits = model(batch_tensor)
                    probs = torch.sigmoid(logits).cpu().numpy()
                    
                    # 3. Reassemble the probabilities back into the full-size maps
                    for i, (bx, by) in enumerate(coords_batch):
                        prob_cloud = probs[i, 0, :, :] * window_2d
                        prob_water = probs[i, 1, :, :] * window_2d
                        
                        prob_map_cloud[by:by+tile_size, bx:bx+tile_size] += prob_cloud
                        prob_map_water[by:by+tile_size, bx:bx+tile_size] += prob_water
                        count_map[by:by+tile_size, bx:bx+tile_size] += window_2d
                    
                    # 4. Clear lists for the next batch
                    tiles_batch = []
                    coords_batch = []

    final_cloud_prob = (prob_map_cloud / (count_map + 1e-7))[:h, :w]
    final_water_prob = (prob_map_water / (count_map + 1e-7))[:h, :w]
    
    b2 = scaled_tensor[0, :h, :w]
    b3 = scaled_tensor[1, :h, :w]
    b4 = scaled_tensor[2, :h, :w]
    b8 = scaled_tensor[3, :h, :w]
    
    brightness = np.sqrt(b2**2 + b3**2 + b4**2)
    ndwi = (b3 - b8) / (b3 + b8 + 1e-5)

    base_cloud_mask = ((final_cloud_prob > 0.5) & (brightness > 0.35)).astype(np.uint8)
    
    cloud_buffer_kernel = np.ones((10, 10), np.uint8)
    cloud_and_shadow_mask = cv2.dilate(base_cloud_mask, cloud_buffer_kernel, iterations=1)

    raw_water_mask = (final_water_prob > 0.35) | (ndwi > 0.15)
    
    water_mask = raw_water_mask & (cloud_and_shadow_mask == 0) & (ndwi > -0.1)
    clean_mask = water_mask.astype(np.uint8)

    close_kernel = np.ones((3, 3), np.uint8)
    clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, close_kernel)

    open_kernel = np.ones((2, 2), np.uint8)
    clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_OPEN, open_kernel)

    contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    min_area = 50
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            cv2.drawContours(clean_mask, [cnt], -1, 0, -1)

    return clean_mask * 255

def process_sar_image(tiff_path, preview_filename):
    if not os.path.exists(tiff_path): return None, None
    
    sar_db = tiff.imread(tiff_path).astype(np.float32)
    
    water_mask = ((sar_db < -16) & (sar_db > -90)).astype(np.uint8) * 255
    
    close_kernel = np.ones((3, 3), np.uint8)
    water_mask = cv2.morphologyEx(water_mask, cv2.MORPH_CLOSE, close_kernel)
    
    visual = np.clip((sar_db + 25) / 25.0, 0, 1) * 255
    visual = visual.astype(np.uint8)
    
    h, w = visual.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = visual 
    rgba[:, :, 1] = visual 
    rgba[:, :, 2] = visual 
    
    rgba[:, :, 3] = np.where(sar_db < -90, 0, 255)
    
    save_path = os.path.join(DOWNLOADS_DIR, preview_filename)
    cv2.imwrite(save_path, rgba)
    
    return water_mask, preview_filename

def create_rgb_preview(tiff_path, filename):
    if not os.path.exists(tiff_path): return None
    image = tiff.imread(tiff_path).astype(np.float32)

    if image.ndim == 2:
        rgb = np.zeros((image.shape[0], image.shape[1], 3), dtype=np.uint8)
        rgb[image == 255] = [255, 0, 0] 
        save_path = os.path.join(DOWNLOADS_DIR, filename)
        cv2.imwrite(save_path, rgb)
        return filename

    if image.shape[0] == 6: image = np.transpose(image, (1, 2, 0))
    if np.max(image) > 1.0: image = image / 10000.0
    
    rgb = image[:, :, [0, 1, 2]]
    rgb = np.clip(rgb * 3.0, 0, 1) * 255
    rgb = rgb.astype(np.uint8)
    
    gaussian = cv2.GaussianBlur(rgb, (0, 0), 2.0)
    sharpened = cv2.addWeighted(rgb, 1.5, gaussian, -0.5, 0)
    
    save_path = os.path.join(DOWNLOADS_DIR, filename)
    cv2.imwrite(save_path, sharpened)
    return filename

def create_overlay_png(mask, color, filename):
    if mask is None: return None
    h, w = mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    b, g, r = color
    rgba[mask == 255, 0] = b
    rgba[mask == 255, 1] = g
    rgba[mask == 255, 2] = r
    rgba[mask == 255, 3] = 180
    save_path = os.path.join(DOWNLOADS_DIR, filename)
    cv2.imwrite(save_path, rgba)
    return filename

# --- 6. AI REPORTING ---

def generate_flood_report(stats, coords, dates, image_path):      
    try:          
        gemini_api_key = os.environ.get("GEMINI_API_KEY")            
        if not gemini_api_key:              
            return "Error: AI Report unavailable. GEMINI_API_KEY missing in environment."  

        if not os.path.exists(image_path):
            return "Error: AI Report unavailable. Flood image overlay not found."

        client = genai.Client(api_key=gemini_api_key)
        
        baseline_date = dates.get('baseline', 'Unknown Baseline')
        latest_date = dates.get('latest', 'Unknown Date')
        base_sq = stats.get('baseline_sq_km', 0.0)
        curr_sq = stats.get('current_sq_km', 0.0)
        flood_sq = stats.get('flood_sq_km', 0.0)
        
        with Image.open(image_path) as img:
            prompt = f"""          
You are a Lead Geospatial Intelligence Analyst generating an executive-level Flood Damage and Loss Assessment (DaLA) report. 
I have provided a satellite image overlay. The red pixels definitively indicate algorithmic detections of newly accumulated floodwater.          

CONTEXTUAL TELEMETRY:          
- Bounding Box Coordinates: {coords}          
- Baseline Imagery Date: {baseline_date}
- Post-Flood Capture Date: {latest_date}          
- Pre-flood Water Extent: {base_sq:.2f} sq km          
- Current Total Water Extent: {curr_sq:.2f} sq km          
- Net New Inundation Area: {flood_sq:.2f} sq km          

YOUR DIRECTIVES:
1. Be Authoritative: Eliminate all speculative language (e.g., do not use "likely," "suggests," or "possibly"). Make definitive statements based on the visual evidence and telemetry provided. If a factor is indistinguishable, state that it cannot be determined at this resolution rather than guessing.
2. Be Analytical: Do not just read the numbers back. Calculate the percentage increase in water extent and explain what that scale of increase means for the terrain visible in the image.
3. Be Plain Text: You must output strictly in plain text. DO NOT use markdown formatting, asterisks, hashes, bolding, or special characters. Use standard ALL CAPS for your headers.

REQUIRED REPORT STRUCTURE:
EXECUTIVE SUMMARY
Provide a bottom-line-up-front (BLUF) statement summarizing the severity and scale of the inundation event.

GEOSPATIAL & CLIMATOLOGICAL CONTEXT
Identify the specific region in Pakistan based on the coordinates. Correlate the capture dates with known seasonal weather patterns (e.g., monsoon cycles or glacial melt) to establish the primary driver of the event.

INUNDATION METRICS & MORPHOLOGY
Analyze the quantitative data. Describe the morphological spread of the floodwaters (e.g., riverine overspill, pooling in low-lying plains, or flash flood patterns) based strictly on the shape and distribution of the red overlay.

INFRASTRUCTURE & SOCIO-ECONOMIC IMPACT
Examine the base imagery beneath the flood mask. Definitively state the types of terrain affected (e.g., cultivated agricultural plots, dense urban grids, rural transit corridors). Outline the immediate operational impacts on these specific sectors.

MODEL CONFIDENCE & FALSE POSITIVE ANALYSIS
Critically evaluate the segmentation mask. Identify specific areas in the image where the model may have misclassified topographical shadows, dense cloud shadows, or highly reflective urban surfaces as water. 

STRATEGIC DIRECTIVES
Provide 3 highly specific, actionable recommendations for on-the-ground disaster response agencies based on the exact terrain and impact identified above.
"""  

            config = types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.9,
            )

            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=[img, prompt],
                config=config
            )
            
            if response.text:
                return response.text.strip()
            else:
                return "Error: Model returned an empty response."
            
    except Exception as e:
        import traceback
        print(f"❌ AI Report Error: {e}\n{traceback.format_exc()}", flush=True)
        return "Error: AI Report generation failed due to an internal system error."


# --- 7. MAIN ENDPOINTS ---

@app.route('/api/detect_stream', methods=['POST'])
def detect_stream():
    data = request.json
    coords = data.get('bbox')
    apply_buffer = data.get('apply_buffer', True) 
    
    target_date_str = data.get('target_date')
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    else:
        target_date = datetime.now()
        
    session_id = str(uuid.uuid4())
    session_logs = []
    
    def generate_process():
        def emit_log(progress, message):
            session_logs.append({"progress": progress, "log": message, "timestamp": datetime.now().isoformat()})
            return json.dumps({"progress": progress, "log": message}) + "\n"

        yield emit_log(5, "🌍 Locking Coordinates & Validating Dates...")
        
        start_latest = target_date - timedelta(days=15)
        end_latest = target_date + timedelta(days=5)
        interval_latest = (start_latest.strftime('%Y-%m-%d'), end_latest.strftime('%Y-%m-%d'))
        
        target_year = target_date.year
        baseline_year = target_year - 1 if target_date.month < 6 else target_year
        interval_baseline = (f"{baseline_year}-04-01", f"{baseline_year}-05-31")
        
        yield emit_log(15, f"📡 Building Optical Composite ({interval_latest[0]} to {interval_latest[1]})...")
        
        path_latest, date_latest, src_latest, cloud_percent = fetch_optical_composite(coords, interval_latest, f"{session_id}_latest")
        if cloud_percent is None: cloud_percent = 100 

        if path_latest and cloud_percent <= 85.0:
            yield emit_log(30, f"🧠 Optical Rescued ({cloud_percent:.1f}% Dead Pixels). Running U-Net++...")
            mask_latest = predict_water_mask(path_latest)
            rgb_latest = create_rgb_preview(path_latest, f"{session_id}_rgb_latest.jpg")
            
            yield emit_log(50, "📡 Fetching Dry-Season Baseline (Optical)...")
            path_pre, src_pre = fetch_dynamic_world_baseline(coords, interval_baseline, f"{session_id}_previous")
            date_pre = f"{interval_baseline[0]} to {interval_baseline[1]}"
            
            if path_pre:
                mask_pre = tiff.imread(path_pre).astype(np.uint8)
                rgb_pre = create_rgb_preview(path_pre, f"{session_id}_rgb_previous.jpg")
            else:
                mask_pre = np.zeros_like(mask_latest)
                rgb_pre = None
                
        else:
            yield emit_log(30, f"⛈️ Optical Failed ({cloud_percent:.1f}% Dead Pixels). Switching to SAR Payload...")
            path_latest, date_latest, src_latest = fetch_sar_data(coords, interval_latest, f"{session_id}_latest", is_baseline=False)
            
            if not path_latest:
                yield json.dumps({"error": "Critical Error: Failed to acquire both Optical and SAR fallback data."}) + "\n"
                return
                
            mask_latest, rgb_latest = process_sar_image(path_latest, f"{session_id}_rgb_latest_sar.png")
            
            yield emit_log(50, "📡 Fetching Homogeneous SAR Baseline...")
            path_pre, date_pre_raw, src_pre = fetch_sar_data(coords, interval_baseline, f"{session_id}_previous", is_baseline=True)
            date_pre = f"{interval_baseline[0]} to {interval_baseline[1]}"
            
            if path_pre:
                mask_pre, rgb_pre = process_sar_image(path_pre, f"{session_id}_rgb_previous_sar.png")
            else:
                mask_pre = np.zeros_like(mask_latest)
                rgb_pre = None

        yield emit_log(70, "🌊 Aligning Baseline Maps...")
        if mask_latest.shape != mask_pre.shape:
             mask_pre = cv2.resize(mask_pre, (mask_latest.shape[1], mask_latest.shape[0]), interpolation=cv2.INTER_NEAREST)

        yield emit_log(80, "🌊 Generating Flood Difference...")
        if apply_buffer:
            buffer_kernel = np.ones((5, 5), np.uint8)
            mask_pre_buffered = cv2.dilate(mask_pre, buffer_kernel, iterations=1)
            flood_mask = cv2.bitwise_and(mask_latest, cv2.bitwise_not(mask_pre_buffered))  
        else:
            flood_mask = cv2.bitwise_and(mask_latest, cv2.bitwise_not(mask_pre)) 
        
        base_url = request.host_url.rstrip('/')  
        
        yield emit_log(85, "🎨 Generating Visual Overlays...")
        url_latest = create_overlay_png(mask_latest, [255, 0, 0], f"{session_id}_overlay_latest.png")          
        url_pre = create_overlay_png(mask_pre, [255, 255, 0], f"{session_id}_overlay_previous.png")          
        url_flood = create_overlay_png(flood_mask, [0, 0, 255], f"{session_id}_overlay_flood.png")  

        yield emit_log(90, "📊 Calculating Spatial Metrics...")
        n, s, e, w = coords['north'], coords['south'], coords['east'], coords['west']
        current_scale = 50 if max(n - s, e - w) > 0.5 else 10
        pixel_to_sq_km = (current_scale ** 2) / 1_000_000    
        stats = {              
            "baseline_sq_km": np.count_nonzero(mask_pre == 255) * pixel_to_sq_km,              
            "current_sq_km": np.count_nonzero(mask_latest == 255) * pixel_to_sq_km,              
            "flood_sq_km": np.count_nonzero(flood_mask == 255) * pixel_to_sq_km,          
        }          
        dates = {"baseline": date_pre, "latest": date_latest}  

        yield emit_log(95, "🤖 Generating AI Assessment Report...")
        flood_image_path = os.path.join(DOWNLOADS_DIR, f"{session_id}_overlay_flood.png")
        ai_report_text = generate_flood_report(stats, coords, dates, flood_image_path)          
        
        yield emit_log(98, "📄 Compiling PDF Report...")
        report_filename = f"flood_assessment_report_{session_id}.pdf"          
        report_path = os.path.join(DOWNLOADS_DIR, report_filename)  

        pdf_img_path = os.path.join(DOWNLOADS_DIR, f"pdf_img_{session_id}.jpg")
        
        if rgb_latest:
            base_img = cv2.imread(os.path.join(DOWNLOADS_DIR, rgb_latest))
            if base_img is not None and base_img.shape[2] == 4:
                base_img = cv2.cvtColor(base_img, cv2.COLOR_BGRA2BGR)
        else:
            base_img = None
        
        if base_img is not None:  
            pdf_img = base_img.copy()  
            
            if flood_mask.shape != pdf_img.shape[:2]:
                safe_flood_mask = cv2.resize(flood_mask, (pdf_img.shape[1], pdf_img.shape[0]), interpolation=cv2.INTER_NEAREST)
            else:
                safe_flood_mask = flood_mask
                
            pdf_img[safe_flood_mask == 255] = (0, 0, 255)  
            cv2.imwrite(pdf_img_path, pdf_img)  
        else:  
            pdf_img_path = flood_image_path 

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 18)
        pdf.cell(0, 15, "SatVision Flood Assessment Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        pdf.image(pdf_img_path, x=15, w=180)
        pdf.ln(10)
        pdf.set_font("helvetica", size=11)
        pdf.multi_cell(0, 6, text=ai_report_text, markdown=True)
        pdf.output(report_path)
        
        yield emit_log(100, "✅ Detection Complete!")
        
        if generations_col is not None:
            generation_record = {
                "session_id": session_id,
                "timestamp": datetime.now(),
                "coordinates": coords,
                "target_date": target_date_str,
                "metadata": {
                    "latest_source": src_latest,
                    "baseline_source": src_pre,
                    "latest_date": date_latest,
                    "baseline_date": date_pre
                },
                "metrics": stats,
                "ai_report": ai_report_text,
                "logs": session_logs,
                "feedback": None
            }
            try:
                generations_col.insert_one(generation_record)
            except Exception as db_err:
                print(f"❌ DB Insert Failed: {db_err}")
        
        yield json.dumps({
            "progress": 100,
            "session_id": session_id,
            "result": {
                "latest": f"{base_url}/mask/{url_latest}",
                "previous": f"{base_url}/mask/{url_pre}",
                "flood": f"{base_url}/mask/{url_flood}"
            },
            "meta": {
                "latest_date": date_latest,
                "previous_date": date_pre,
                "latest_source": src_latest,
                "previous_source": src_pre,
                "latest_rgb": f"{base_url}/mask/{rgb_latest}" if rgb_latest else None,
                "previous_rgb": f"{base_url}/mask/{rgb_pre}" if rgb_pre else None
            },
            "report": {
                "text": ai_report_text,
                "download_url": f"{base_url}/mask/{report_filename}",
                "metrics": stats
            }
        }) + "\n"
        
    return Response(stream_with_context(generate_process()), mimetype='application/json')

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    if generations_col is None:
        return {"error": "Database unavailable"}, 503

    data = request.json
    session_id = data.get('session_id')
    feedback_text = data.get('feedback_text')
    rating = data.get('rating')

    if not session_id or not feedback_text:
        return {"error": "Missing session_id or feedback_text"}, 400

    try:
        result = generations_col.update_one(
            {"session_id": session_id},
            {"$set": {
                "feedback": {
                    "text": feedback_text,
                    "rating": rating,
                    "submitted_at": datetime.now()
                }
            }}
        )
        
        if result.matched_count == 0:
            return {"error": "Session ID not found"}, 404
            
        return {"message": "Feedback recorded successfully"}, 200
        
    except Exception as e:
        print(f"❌ Feedback Update Error: {e}", flush=True)
        return {"error": "Internal database error"}, 500

@app.route('/mask/<filename>')
def serve_mask(filename):
    is_pdf = filename.endswith('.pdf')
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=is_pdf)

if __name__ == '__main__':
    print("🚀 Flood Backend Running...", flush=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("FLASK_PORT", os.environ.get("PORT", 5000))), threaded=True)