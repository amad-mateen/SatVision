"""
Flask Application Factory.
"""

from flask import Flask
from flask_cors import CORS
from src import config
from src.database import mongo as mongo_service
from src.database import gee as gee_service
from src.services import model as model_service
from src.routes.health import health_bp
from src.routes.detection import detection_bp
from src.routes.feedback import feedback_bp
from src.routes.assets import assets_bp


def create_app():
    """
    Application factory function.
    """
    app = Flask(__name__)
    
    # Run dynamic environment sanity validation
    config.validate_environment()
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    app.config['JSON_SORT_KEYS'] = False
    
    # ========================================================================
    # CORS SETUP
    # ========================================================================
    CORS(app)
    
    # ========================================================================
    # INITIALIZATION: EARTH ENGINE
    # ========================================================================
    try:
        gee_service.initialize_earth_engine()
    except Exception as e:
        config.logger.warning(f"⚠️ Earth Engine initialization warning: {e}")
    
    # ========================================================================
    # INITIALIZATION: MONGODB
    # ========================================================================
    db, generations_col = mongo_service.initialize_mongodb()
    
    # ========================================================================
    # INITIALIZATION: MODEL
    # ========================================================================
    model = model_service.initialize_model()
    
    # ========================================================================
    # BLUEPRINT REGISTRATION
    # ========================================================================
    # Explicitly registering routing layers
    app.register_blueprint(health_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(feedback_bp)
    
    # Keep assets mounted directly to the root url context /mask/<filename> 
    # to perfectly mirror the old working monolithic environment
    app.register_blueprint(assets_bp)
    
    # ========================================================================
    # ERROR HANDLERS
    # ========================================================================
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error"}, 500
    
    return app