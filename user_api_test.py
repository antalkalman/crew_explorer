import os
import time
import requests
import pandas as pd

# === CONFIG ===

desktop_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/API_test"
laptop_path = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/API_test"
base_dir = desktop_path if os.path.exists(desktop_path) else laptop_path

token = "4|FtRaHbpkyP7dj6geLbqQiUc2WznEEqbRhvOD2xPO1cee3bfd"
base_url = "https://manager.crewcall.hu/api/"
headers = {"Authorization": f"Bearer {token}"}

output_path = os.path.join(base_dir, "CrewManager_Vendors.csv")
os.makedirs(base_dir, exist_ok=True)

# === FUNCTION: Fetch data from Crew Manager API ===
def fetch_data(endpoint, retries=3, delay=5):
    for attempt in range(retries):
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=30)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} – Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise

# === FETCH VENDORS ===
vendors = fetch_data("vendor")

# === SAVE TO CSV ===
df_vendors = pd.DataFrame(vendors)
df_vendors.to_csv(output_path, index=False)
print(f"✅ Vendor data saved to:\n{output_path}")
