"""
Flask Blueprints for feedback submission endpoint.
"""

from flask import Blueprint, request
from datetime import datetime
from src.database.mongo import get_generations_collection

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api')


@feedback_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """
    Submit feedback for a detection session.
    
    Expects JSON POST body:
    {
        "session_id": str,
        "feedback_text": str,
        "rating": int (optional)
    }
    """
    generations_col = get_generations_collection()
    
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