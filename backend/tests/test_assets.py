import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend directory to sys.path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Patch dependencies for offline testing
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

    def test_serve_missing_mask_returns_404(self):
        # Mock os.path.exists to return False to simulate missing files
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            response = self.client.get('/mask/nonexistent_file.png')
            self.assertEqual(response.status_code, 404)

    def test_serve_existing_mask_calls_send_from_directory(self):
        # Mock os.path.exists to True and intercept send_from_directory
        with patch('os.path.exists') as mock_exists, \
             patch('src.routes.assets.send_from_directory') as mock_send:
            mock_exists.return_value = True
            mock_send.return_value = "mock_file_content"
            
            response = self.client.get('/mask/session123/existing_file.png')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data.decode('utf-8'), "mock_file_content")
            
            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            self.assertTrue(args[0].endswith(os.path.join('server_downloads', 'session123')))
            self.assertEqual(args[1], 'existing_file.png')

if __name__ == '__main__':
    unittest.main()
