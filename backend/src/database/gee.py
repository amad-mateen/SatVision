"""
Google Earth Engine initialization and authentication.
"""

import json
import ee
from src import config


def initialize_earth_engine():
    """
    Initialize Earth Engine with service account credentials or local auth.
    """
    print("🌍 Initializing Earth Engine...", flush=True)
    
    try:
        if config.EE_CREDENTIALS_JSON:
            # Use service account credentials from environment
            key_dict = json.loads(config.EE_CREDENTIALS_JSON)
            from google.oauth2 import service_account
            
            credentials = service_account.Credentials.from_service_account_info(
                key_dict,
                scopes=['https://www.googleapis.com/auth/earthengine']
            )
            ee.Initialize(credentials, project=config.EE_PROJECT_ID)
            print("✅ Earth Engine Linked via Service Account.", flush=True)
        else:
            # Use local authentication (cached credentials)
            ee.Initialize(project=config.EE_PROJECT_ID)
            print("✅ Earth Engine Linked via Local Auth.", flush=True)
    except Exception as e:
        print(f"❌ Earth Engine Init Failed: {e}", flush=True)
        raise