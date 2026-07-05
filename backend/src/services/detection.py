"""
Concurrency-insulated, adaptive resolution flood detection pipeline.
"""

import os
import json
from datetime import datetime, timedelta
import numpy as np
import tifffile as tiff
import cv2
import uuid
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from src import config
from src.services import model as model_service
from src.services import gee_service
from src.services import cv2 as cv2_service
from src.services import gemini as gemini_service
from src.database.mongo import get_generations_collection


def run_detection_pipeline(coords, target_date, apply_buffer=True, base_url="http://localhost:5000"):
    """
    Insulated pipeline preventing concurrent leakages by running operations 
    inside runtime session directories and scaling resolution dynamically.
    """
    session_id = str(uuid.uuid4())
    
    # CRITICAL: Create isolated concurrent session folder workspace
    session_dir = os.path.join(config.DOWNLOADS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    session_logs = []
    
    def emit_log(progress, message):
        session_logs.append({
            "progress": progress,
            "log": message,
            "timestamp": datetime.now().isoformat()
        })
        return json.dumps({"progress": progress, "log": message}) + "\n"
    
    yield emit_log(5, "🌍 Locking Coordinates & Validating Dates...")
    
    start_latest = target_date - timedelta(days=15)
    end_latest = target_date + timedelta(days=5)
    interval_latest = (start_latest.strftime('%Y-%m-%d'), end_latest.strftime('%Y-%m-%d'))
    
    target_year = target_date.year
    baseline_year = target_year - 1 if target_date.month < 6 else target_year
    interval_baseline = (f"{baseline_year}-04-01", f"{baseline_year}-05-31")
    
    # Determine dynamic scale parameters based on area span size to prevent timeouts (e.g. Lake Manchar)
    n, s, e, w = coords['north'], coords['south'], coords['east'], coords['west']
    span = max(n - s, e - w)
    
    if span > 0.6:
        current_scale = config.SCALE_XLARGE  # 90m scale for mega fields like Dadu
        yield emit_log(10, f"⚡ Massive Region Detected ({span:.2f}°). Optimizing resolution scale to {current_scale}m to prevent timeouts...")
    elif span > 0.2:
        current_scale = config.SCALE_LARGE   # 40m scale
        yield emit_log(10, f"⚡ Large Region Detected ({span:.2f}°). Adjusting resolution scale to {current_scale}m...")
    else:
        current_scale = config.SCALE_SMALL   # 10m crisp resolution scale
    
    yield emit_log(15, f"📡 Building Cloud-Free Composite ({interval_latest[0]} to {interval_latest[1]})...")
    
    # Pass down the runtime session directory path context instead of flat paths
    path_latest, date_latest, src_latest, cloud_percent = gee_service.fetch_optical_composite(
        coords, interval_latest, os.path.join(session_id, f"{session_id}_latest"), scale=current_scale
    )
    if cloud_percent is None:
        cloud_percent = 100
    
    if path_latest and cloud_percent <= config.OPTICAL_CLEAR_THRESHOLD:
        yield emit_log(30, f"🧠 Optical Clear ({cloud_percent:.1f}% cloud cover). Launching inference...")
        
        mask_latest = model_service.predict_water_mask(path_latest)
        if mask_latest.ndim == 3:
            mask_latest = mask_latest[:, :, 0]
            
        rgb_latest = cv2_service.create_rgb_preview(path_latest, os.path.join(session_id, f"{session_id}_rgb_latest.jpg"))
        
        yield emit_log(50, "📡 Fetching Dry-Season Anchor Baseline...")
        path_pre, src_pre = gee_service.fetch_dynamic_world_baseline(
            coords, interval_baseline, os.path.join(session_id, f"{session_id}_previous"), scale=current_scale
        )
        date_pre = f"{interval_baseline[0]} to {interval_baseline[1]}"
        
        if path_pre:
            mask_pre = tiff.imread(path_pre).astype(np.uint8)
            if mask_pre.ndim == 3:
                mask_pre = mask_pre[:, :, 0]
            rgb_pre = cv2_service.create_rgb_preview(path_pre, os.path.join(session_id, f"{session_id}_rgb_previous.jpg"))
        else:
            mask_pre = np.zeros_like(mask_latest)
            rgb_pre = None
    else:
        yield emit_log(30, f"⛈️ Cloud Blockage Obstruction ({cloud_percent:.1f}% cover). Activating Radar SAR Fallback...")
        
        path_latest, date_latest, src_latest = gee_service.fetch_sar_data(
            coords, interval_latest, os.path.join(session_id, f"{session_id}_latest"), is_baseline=False, scale=current_scale
        )
        
        if not path_latest:
            yield json.dumps({"error": "Critical Error: Failed to acquire tracking maps."}) + "\n"
            return
        
        mask_latest, rgb_latest = cv2_service.process_sar_image(
            path_latest, os.path.join(session_id, f"{session_id}_rgb_latest_sar.png")
        )
        if mask_latest.ndim == 3:
            mask_latest = mask_latest[:, :, 0]
        
        yield emit_log(50, "📡 Fetching Baseline SAR Map Matrix...")
        path_pre, date_pre_raw, src_pre = gee_service.fetch_sar_data(
            coords, interval_baseline, os.path.join(session_id, f"{session_id}_previous"), is_baseline=True, scale=current_scale
        )
        date_pre = f"{interval_baseline[0]} to {interval_baseline[1]}"
        
        if path_pre:
            mask_pre, rgb_pre = cv2_service.process_sar_image(
                path_pre, os.path.join(session_id, f"{session_id}_rgb_previous_sar.png")
            )
            if mask_pre.ndim == 3:
                mask_pre = mask_pre[:, :, 0]
        else:
            mask_pre = np.zeros_like(mask_latest)
            rgb_pre = None
    
    yield emit_log(70, "🌊 Conforming Geospatial Matrices...")
    if mask_latest.shape != mask_pre.shape:
        mask_pre = cv2.resize(mask_pre, (mask_latest.shape[1], mask_latest.shape[0]), interpolation=cv2.INTER_NEAREST)
    
    yield emit_log(80, "🌊 Isolating Extent Variance (Change Vector)...")
    if apply_buffer:
        buffer_kernel = np.ones((5, 5), np.uint8)
        mask_pre_buffered = cv2.dilate(mask_pre, buffer_kernel, iterations=1)
        flood_mask = cv2.bitwise_and(mask_latest, cv2.bitwise_not(mask_pre_buffered))
    else:
        flood_mask = cv2.bitwise_and(mask_latest, cv2.bitwise_not(mask_pre))
    
    yield emit_log(85, "🎨 Rendering Semi-Transparent Visual Overlays...")
    raw_url_latest = cv2_service.create_overlay_png(mask_latest, [255, 0, 0], os.path.join(session_id, f"{session_id}_overlay_latest.png"))
    raw_url_pre = cv2_service.create_overlay_png(mask_pre, [255, 255, 0], os.path.join(session_id, f"{session_id}_overlay_previous.png"))
    raw_url_flood = cv2_service.create_overlay_png(flood_mask, [0, 0, 255], os.path.join(session_id, f"{session_id}_overlay_flood.png"))
    
    yield emit_log(90, "📊 Calculating Inundation Area Metrics...")
    pixel_to_sq_km = config.calculate_pixel_to_sq_km(current_scale)
    stats = {
        "baseline_sq_km": float(np.count_nonzero(mask_pre == 255) * pixel_to_sq_km),
        "current_sq_km": float(np.count_nonzero(mask_latest == 255) * pixel_to_sq_km),
        "flood_sq_km": float(np.count_nonzero(flood_mask == 255) * pixel_to_sq_km),
    }
    dates = {"baseline": date_pre, "latest": date_latest}
    
    yield emit_log(95, "🤖 Generating Multi-modal Executive AI Summary Report...")
    flood_image_path = os.path.join(config.DOWNLOADS_DIR, session_id, f"{session_id}_overlay_flood.png")
    
    try:
        ai_report_text = gemini_service.generate_flood_report(stats, coords, dates, flood_image_path)
    except Exception as gem_err:
        ai_report_text = "The satellite flood assessment executive summary text is currently undergoing maintenance."

    yield emit_log(98, "📄 Compiling Document Artifact PDF...")
    report_filename = f"flood_assessment_report_{session_id}.pdf"
    report_path = os.path.join(config.DOWNLOADS_DIR, session_id, report_filename)
    pdf_img_path = os.path.join(config.DOWNLOADS_DIR, session_id, f"pdf_img_{session_id}.jpg")
    
    if rgb_latest:
        clean_rgb_latest = os.path.basename(rgb_latest)
        base_img = cv2.imread(os.path.join(config.DOWNLOADS_DIR, session_id, clean_rgb_latest))
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
    
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 18)
        pdf.cell(0, 15, "SatVision Flood Assessment Report", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(5)
        pdf.image(pdf_img_path, x=15, w=180)
        pdf.ln(10)
        pdf.set_font("helvetica", size=11)
        safe_pdf_text = str(ai_report_text).encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, text=safe_pdf_text)
        pdf.output(report_path)
    except Exception as pdf_err:
        config.logger.error(f"❌ PDF Engine Failed: {pdf_err}")
    
    yield emit_log(100, "✅ Detection Pipeline Complete!")
    
    generations_col = get_generations_collection()
    if generations_col is not None:
        generation_record = {
            "session_id": session_id,
            "timestamp": datetime.now(),
            "coordinates": coords,
            "target_date": target_date.strftime('%Y-%m-%d'),
            "metrics": stats,
            "ai_report": ai_report_text,
            "logs": session_logs,
            "feedback": None
        }
        try:
            generations_col.insert_one(generation_record)
        except Exception as db_err:
            config.logger.error(f"❌ DB Write Blocked: {db_err}")
            
    # Sanitize URLs to point to unique session paths: e.g. base_url/mask/session_id/filename.png
    c_lat = f"{session_id}/{os.path.basename(raw_url_latest)}" if raw_url_latest else ""
    c_pre = f"{session_id}/{os.path.basename(raw_url_pre)}" if raw_url_pre else ""
    c_fld = f"{session_id}/{os.path.basename(raw_url_flood)}" if raw_url_flood else ""
    c_rgb_lat = f"{session_id}/{os.path.basename(rgb_latest)}" if rgb_latest else None
    c_rgb_pre = f"{session_id}/{os.path.basename(rgb_pre)}" if rgb_pre else None

    yield json.dumps({
        "progress": 100,
        "session_id": session_id,
        "result": {
            "latest": f"{base_url.rstrip('/')}/mask/{c_lat}",
            "previous": f"{base_url.rstrip('/')}/mask/{c_pre}",
            "flood": f"{base_url.rstrip('/')}/mask/{c_fld}"
        },
        "meta": {
            "latest_date": date_latest,
            "previous_date": date_pre,
            "latest_source": src_latest,
            "previous_source": src_pre,
            "latest_rgb": f"{base_url.rstrip('/')}/mask/{c_rgb_lat}" if c_rgb_lat else None,
            "previous_rgb": f"{base_url.rstrip('/')}/mask/{c_rgb_pre}" if c_rgb_pre else None
        },
        "report": {
            "text": ai_report_text,
            "download_url": f"{base_url.rstrip('/')}/mask/{session_id}/{report_filename}",
            "metrics": stats
        }
    }) + "\n"