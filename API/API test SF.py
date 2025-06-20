import os
import time
import requests
import pandas as pd

# API token and base URL
token = "2|cNxI00wYuPRjpO7N6N84dowZfybyXoaAn1y98nw76a3e656f"
base_url = "https://manager.crewcall.hu/api/"
headers = {"Authorization": f"Bearer {token}"}

# Output path
output_dir = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/API_test"
output_file = os.path.join(output_dir, "CrewManager_StartForms.csv")

# Ensure folder exists
os.makedirs(output_dir, exist_ok=True)

# Retry logic
max_retries = 3
retry_delay = 5  # seconds

for attempt in range(max_retries):
    try:
        response = requests.get(f"{base_url}startform", headers=headers, timeout=30)
        response.raise_for_status()
        sfs = response.json().get("data", [])

        # Normalize nested fields like company_data and personal_data
        df = pd.json_normalize(sfs)

        # Optional: select or reorder columns here if needed
        df.to_csv(output_file, index=False)
        print(f"✅ Start Forms saved to: {output_file}")
        break
    except requests.exceptions.RequestException as e:
        print(f"❌ Attempt {attempt + 1} failed: {e}")
        if attempt < max_retries - 1:
            print(f"⏳ Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("🚨 All retry attempts failed.")
