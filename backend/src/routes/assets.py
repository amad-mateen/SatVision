"""
Flask Blueprints for serving generated assets across isolated concurrent sessions.
"""

import os
from flask import Blueprint, send_from_directory, abort
from src import config

assets_bp = Blueprint('assets', __name__)

@assets_bp.route('/mask/<path:filename>')
def serve_mask(filename):
    """
    Serve generated assets safely by supporting flat configurations or session sub-folders.
    """
    # Try locating file in isolated session directory first, fallback to root downloads
    parts = filename.split('/')
    if len(parts) > 1:
        # e.g. /mask/session_uuid/filename.png
        safe_path = os.path.join(config.DOWNLOADS_DIR, filename)
    else:
        # Check if the filename itself starts with a uuid prefix we can extract
        prefix = filename.split('_')[0]
        possible_session_dir = os.path.join(config.DOWNLOADS_DIR, prefix)
        if os.path.exists(os.path.join(possible_session_dir, filename)):
            return send_from_directory(possible_session_dir, filename, as_attachment=filename.lower().endswith('.pdf'))
        
        safe_path = os.path.join(config.DOWNLOADS_DIR, filename)
        
    if not os.path.exists(safe_path):
        print(f"❌ Asset Serving Failed: File not found at path {safe_path}", flush=True)
        abort(404)
        
    return send_from_directory(
        os.path.dirname(safe_path), 
        os.path.basename(safe_path), 
        as_attachment=filename.lower().endswith('.pdf')
    )