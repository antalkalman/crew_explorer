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
output_file = os.path.join(output_dir, "CrewManager_JobTitles.csv")

# Ensure folder exists
os.makedirs(output_dir, exist_ok=True)

# Retry logic
max_retries = 3
retry_delay = 5  # seconds

for attempt in range(max_retries):
    try:
        response = requests.get(f"{base_url}job_title", headers=headers, timeout=10)
        response.raise_for_status()
        job_titles = response.json().get("data", [])
        df = pd.DataFrame(job_titles)
        df.to_csv(output_file, index=False)
        print(f"✅ Job titles saved to: {output_file}")
        break
    except requests.exceptions.RequestException as e:
        print(f"❌ Attempt {attempt + 1} failed: {e}")
        if attempt < max_retries - 1:
            print(f"⏳ Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("🚨 All retry attempts failed.")
