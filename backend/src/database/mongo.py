"""
MongoDB client initialization and connection management.
"""

from pymongo import MongoClient
from src import config

# Global MongoDB client and database references
_mongo_client = None
_db = None
_generations_col = None


def initialize_mongodb():
    """
    Initialize MongoDB connection with error handling.
    Returns tuple of (db, generations_collection) or (None, None) on failure.
    """
    global _mongo_client, _db, _generations_col
    
    if config.MONGO_URI is None:
        config.logger.warning("⚠️  MongoDB URI not configured (MONGO_URI env var missing)")
        return None, None
    
    try:
        _mongo_client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=5000)
        _db = _mongo_client[config.MONGO_DB_NAME]
        _generations_col = _db[config.MONGO_COLLECTION_NAME]
        
        # Verify connection
        _mongo_client.admin.command('ping')
        config.logger.info("✅ MongoDB Connected Successfully!")
        return _db, _generations_col
    except Exception as e:
        config.logger.error(f"❌ MongoDB Connection Failed: {e}")
        _mongo_client = None
        _db = None
        _generations_col = None
        return None, None


def get_database():
    """Get the initialized database instance."""
    return _db


def get_generations_collection():
    """Get the generations collection instance."""
    return _generations_col


def close_mongodb():
    """Close MongoDB connection."""
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        config.logger.info("✅ MongoDB connection closed")