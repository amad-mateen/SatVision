"""
Flask Blueprints for flood detection endpoint with streaming response.
"""

from flask import Blueprint, request, Response, stream_with_context
from datetime import datetime
from src.services import detection as detection_service

detection_bp = Blueprint('detection', __name__, url_prefix='/api')


@detection_bp.route('/detect_stream', methods=['POST'])
def detect_stream():
    """
    Main detection endpoint with streaming response.
    
    Expects JSON POST body:
    {
        "bbox": {"north": float, "south": float, "east": float, "west": float},
        "apply_buffer": bool (optional, default true),
        "target_date": "YYYY-MM-DD" (optional, defaults to today)
    }
    """
    data = request.json
    coords = data.get('bbox')
    apply_buffer = data.get('apply_buffer', True)
    
    target_date_str = data.get('target_date')
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    else:
        target_date = datetime.now()
    
    def generate_process():
        """Generator for streaming detection results."""
        # Extract base host URL path to capture local domain ports or cloud host spaces dynamically
        base_url = request.host_url.rstrip('/')
        
        # Run detection pipeline orchestration logic with the host URL correctly wired down
        for chunk in detection_service.run_detection_pipeline(
            coords=coords, 
            target_date=target_date, 
            apply_buffer=apply_buffer, 
            base_url=base_url
        ):
            yield chunk
    
    return Response(stream_with_context(generate_process()), mimetype='application/json')