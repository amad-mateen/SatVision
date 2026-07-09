import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend directory to sys.path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Patch initialization dependencies to execute tests offline
        cls.gee_patch = patch('src.database.gee.initialize_earth_engine')
        cls.mongo_patch = patch('src.database.mongo.initialize_mongodb')
        cls.model_patch = patch('src.services.model.initialize_model')
        
        cls.gee_mock = cls.gee_patch.start()
        cls.mongo_mock = cls.mongo_patch.start()
        cls.model_mock = cls.model_patch.start()
        
        cls.mongo_mock.return_value = (MagicMock(), MagicMock())
        cls.model_mock.return_value = MagicMock()
        
        from src.app import create_app
        cls.app = create_app()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.gee_patch.stop()
        cls.mongo_patch.stop()
        cls.model_patch.stop()

    def test_health_check(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode('utf-8'), "✅ SatVision Backend is alive!")

if __name__ == '__main__':
    unittest.main()
