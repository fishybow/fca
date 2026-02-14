#!/usr/bin/env python3
"""
Download the complete amiibo database from amiiboapi.org and cache it locally.
This allows offline lookups without rate limiting concerns.
"""

import json
import requests
from pathlib import Path

def download_amiibo_database(output_file="amiibo_database.json"):
    """
    Download the complete amiibo database from amiiboapi.org.
    
    Args:
        output_file: Path to save the JSON database
    """
    print("Downloading amiibo database from amiiboapi.org...")
    
    try:
        # Fetch all amiibo data
        url = "https://amiiboapi.org/api/amiibo/"
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            print(f"Error: API returned status {response.status_code}")
            return False
        
        data = response.json()
        amiibo_list = data.get("amiibo", [])
        
        if not amiibo_list:
            print("Error: No amiibo data received")
            return False
        
        # Save to file
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully downloaded {len(amiibo_list)} amiibo entries")
        print(f"✓ Saved to: {output_path.absolute()}")
        print(f"✓ File size: {output_path.stat().st_size / (1024*1024):.2f} MB")
        
        return True
        
    except requests.RequestException as e:
        print(f"Error downloading database: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    output_file = sys.argv[1] if len(sys.argv) > 1 else "amiibo_database.json"
    success = download_amiibo_database(output_file)
    
    if not success:
        sys.exit(1)
