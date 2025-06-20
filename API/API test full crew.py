import os
import time
import requests
import pandas as pd
import ast

# API setup
token = "2|cNxI00wYuPRjpO7N6N84dowZfybyXoaAn1y98nw76a3e656f"
base_url = "https://manager.crewcall.hu/api/"
headers = {"Authorization": f"Bearer {token}"}
output_dir = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/API_test"
os.makedirs(output_dir, exist_ok=True)

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

def extract_others(row_val, label):
    """Flatten up to 2 entries of daily/weekly/fee_others"""
    result = {}
    try:
        entries = ast.literal_eval(row_val) if isinstance(row_val, str) else row_val
        if isinstance(entries, list):
            for i in range(min(2, len(entries))):
                item = entries[i] or {}
                result[f"{label} Other {i+1} Name"] = item.get("name", "")
                result[f"{label} Other {i+1} Price"] = item.get("price", "")
                result[f"{label} Other {i+1} Account Code"] = item.get("account_code", "")
    except Exception:
        pass
    return result

# Fetch all data
projects = fetch_data("project")
departments = fetch_data("department")
job_titles = fetch_data("job_title")
startforms = fetch_data("startform")

# Save raw CSVs
pd.DataFrame(projects).to_csv(os.path.join(output_dir, "CrewManager_Projects.csv"), index=False)
pd.DataFrame(departments).to_csv(os.path.join(output_dir, "CrewManager_Departments.csv"), index=False)
pd.DataFrame(job_titles).to_csv(os.path.join(output_dir, "CrewManager_JobTitles.csv"), index=False)
pd.json_normalize(startforms).to_csv(os.path.join(output_dir, "CrewManager_StartForms.csv"), index=False)

# Create lookup dictionaries
project_lookup = {p["id"]: p["name"] for p in projects}
department_lookup = {d["id"]: d["name"] for d in departments}
job_title_lookup = {j["id"]: j["name"] for j in job_titles}

# Normalize StartForms
df_sf = pd.json_normalize(startforms)

# Map foreign keys to human-readable names
df_sf["Project"] = df_sf["project_id"].map(project_lookup)
df_sf["Project department"] = df_sf["project_department_id"].map(department_lookup)
df_sf["Project job title"] = df_sf["project_job_title_id"].map(job_title_lookup)

# Keep user_id only
df_sf["User ID"] = df_sf["user_id"]
df_sf.drop(columns=[col for col in df_sf.columns if col.startswith("user_") and col != "user_id"], inplace=True)

# Flatten nested "others" fields
df_daily = df_sf["daily_others"].apply(lambda x: pd.Series(extract_others(x, "Daily")))
df_weekly = df_sf["weekly_others"].apply(lambda x: pd.Series(extract_others(x, "Weekly")))
df_fee = df_sf["fee_others"].apply(lambda x: pd.Series(extract_others(x, "Fee")))

# Merge all into final DataFrame
df_export = pd.concat([df_sf, df_daily, df_weekly, df_fee], axis=1)

# Save final file with all columns
output_file = os.path.join(output_dir, "Formatted_SFlist.csv")
df_export.to_csv(output_file, index=False)
print(f"✅ Final formatted SF list saved to: {output_file}")
