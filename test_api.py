import requests
import json
import time
import subprocess
import sys

# URL de l'API (supposée tourner localement)
API_URL = "http://localhost:8000/route"

def test_api():
    print("Testing API...")
    
    # Payload de test
    payload = {
        "start": "Cotonou",
        "end": "Parakou",
        "avoid": "Bohicon",
        "season": "dry"
    }
    
    try:
        # Start the server in the background for testing if not already running?
        # For this script, we assume the user will run the server separately or we can try to curl it.
        # But since I cannot easily start a background process and keep it running across tool calls without 'run_command' which might hang,
        # I will just invoke the python function directly to test the logic, OR ask the user to run it.
        # WAIT, I can use `TestClient` from fastapi to test without running a server!
        pass
    except Exception as e:
        print(f"Error: {e}")

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def run_tests():
    print("Running tests with TestClient...")
    
    payload = {
        "start": "Cotonou",
        "end": "Parakou",
        "avoid": "", # Empty avoid for basic test
        "season": "dry"
    }
    
    try:
        response = client.post("/route", json=payload)
        if response.status_code == 200:
            print("✅ Success! Response:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Exception during test: {e}")

if __name__ == "__main__":
    run_tests()
