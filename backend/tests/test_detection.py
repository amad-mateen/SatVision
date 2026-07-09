import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add backend directory to sys.path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestDetection(unittest.TestCase):
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

    def test_detect_stream_success(self):
        # Setup mock payload
        payload = {
            "bbox": {
                "north": 30.5,
                "south": 30.2,
                "east": 69.5,
                "west": 69.2
            },
            "apply_buffer": True
        }
        
        # Mock run_detection_pipeline generator
        def mock_pipeline_gen(*args, **kwargs):
            yield json.dumps({"progress": 10, "log": "Fetching imagery..."}) + "\n"
            yield json.dumps({"progress": 50, "log": "Running UNet++ model..."}) + "\n"
            yield json.dumps({"progress": 100, "result": {"latest": "url1"}}) + "\n"

        with patch('src.services.detection.run_detection_pipeline', side_effect=mock_pipeline_gen) as mock_pipeline:
            response = self.client.post('/api/detect_stream', json=payload)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'application/json')
            
            # Read streaming response
            chunks = response.data.decode('utf-8').split('\n')
            # Filter out empty string due to trailing newline
            chunks = [c for c in chunks if c.strip()]
            
            self.assertEqual(len(chunks), 3)
            first_chunk = json.loads(chunks[0])
            self.assertEqual(first_chunk['progress'], 10)
            self.assertEqual(first_chunk['log'], "Fetching imagery...")
            
            last_chunk = json.loads(chunks[2])
            self.assertEqual(last_chunk['progress'], 100)
            self.assertEqual(last_chunk['result']['latest'], "url1")
            
            # Verify mock call arguments
            mock_pipeline.assert_called_once()
            kwargs = mock_pipeline.call_args[1]
            self.assertEqual(kwargs['coords']['north'], 30.5)
            self.assertEqual(kwargs['apply_buffer'], True)

if __name__ == '__main__':
    unittest.main()
