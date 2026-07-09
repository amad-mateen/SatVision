import os
import unittest
from unittest.mock import patch
import sys

# Add backend directory to sys.path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestConfig(unittest.TestCase):
    def test_default_config_loading(self):
        # Patch os.environ to check default values when env vars are missing
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            from src import config
            importlib.reload(config)
            
            # Assert defaults
            self.assertEqual(config.FLASK_PORT, 5000)
            self.assertEqual(config.MONGO_DB_NAME, "satvision_db")
            self.assertIsNone(config.GEMINI_API_KEY)
            
    def test_env_override_config_loading(self):
        env_vars = {
            "FLASK_PORT": "8080",
            "EE_PROJECT_ID": "test-project-123",
            "GEMINI_API_KEY": "test-gemini-key-xyz"
        }
        with patch.dict(os.environ, env_vars, clear=True):
            import importlib
            from src import config
            importlib.reload(config)
            
            self.assertEqual(config.FLASK_PORT, 8080)
            self.assertEqual(config.EE_PROJECT_ID, "test-project-123")
            self.assertEqual(config.GEMINI_API_KEY, "test-gemini-key-xyz")

if __name__ == '__main__':
    unittest.main()
