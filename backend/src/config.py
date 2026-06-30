import os
import torch

CHECKPOINT_PATH = os.environ.get("CHECKPOINT_PATH", "./models/SatVision_Model.ckpt")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_DIR = os.environ.get("DOWNLOADS_DIR", os.path.join(BASE_DIR, "server_downloads"))
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = "satvision_db"
MONGO_COLLECTION_NAME = "generations"

EE_CREDENTIALS_JSON = os.environ.get("EE_CREDENTIALS")
EE_PROJECT_ID = "gen-lang-client-0114614261"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL_ID = "gemini-2.5-flash"
GEMINI_TEMPERATURE = 0.1
GEMINI_TOP_P = 0.9

S2_CLOUD_THRESHOLD = 35
OPTICAL_CLEAR_THRESHOLD = 85.0
GEE_SCALE_OPTICAL = 100
GEE_REQUEST_TIMEOUT = 240  # Increased timeout limit to protect massive calculations

# Dynamic Tile Segmentation Rules based on Coordinate Span Degrees
MAX_DEG_STEP_XLARGE = 0.80
MAX_DEG_STEP_LARGE = 0.40
MAX_DEG_STEP_SMALL = 0.08

# Meter Resolution Adjustments (Higher numbers = rougher zoom but significantly faster)
SCALE_XLARGE = 90   # For presets like Lake Manchar / Dadu
SCALE_LARGE = 40    # For regional maps
SCALE_SMALL = 10    # For highly focused cities

TILE_SIZE = 256
TILE_OVERLAP_RATIO = 0.5
BATCH_SIZE = 16

CLOUD_BUFFER_KERNEL_SIZE = (10, 10)
CLOUD_DETECTION_THRESHOLD = 0.5
BRIGHTNESS_THRESHOLD = 0.35
NDWI_CLOUD_THRESHOLD = 0.15
NDWI_WATER_THRESHOLD = 0.35
NDWI_MIN_THRESHOLD = -0.1

CLOSE_KERNEL_SIZE = (3, 3)
OPEN_KERNEL_SIZE = (2, 2)
MIN_CONTOUR_AREA = 50

SAR_WATER_DB_RANGE = (-16, -90)
SAR_DB_OFFSET = 25

RGB_BAND_INDICES = [0, 1, 2]
RGB_SCALING_FACTOR = 3.0
OPTICAL_NORMALIZATION_FACTOR = 10000.0
GAUSSIAN_BLUR_SIGMA = 2.0
GAUSSIAN_BLUR_SHARPEN_STRENGTH = 1.5
GAUSSIAN_BLUR_SUBTRACT_STRENGTH = -0.5

OVERLAY_WATER_COLOR_BGR = (255, 0, 0)
OVERLAY_PREVIOUS_COLOR_BGR = (255, 255, 0)
OVERLAY_FLOOD_COLOR_BGR = (0, 0, 255)
OVERLAY_ALPHA = 180

FLASK_HOST = "0.0.0.0"
FLASK_PORT = int(os.environ.get("FLASK_PORT", 7860))
FLASK_THREADED = True

def calculate_pixel_to_sq_km(scale_meters):
    return (scale_meters ** 2) / 1_000_000

S2_BANDS = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12']
S1_POLARIZATION = 'VV'
S1_INSTRUMENT_MODE = 'IW'
DW_WATER_CLASS = 0