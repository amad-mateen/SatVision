"""
Flask Blueprints for health check endpoint.
"""

from flask import Blueprint

health_bp = Blueprint('health', __name__)


@health_bp.route('/', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return "✅ SatVision Backend is alive!", 200