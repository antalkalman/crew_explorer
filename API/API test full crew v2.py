import os
import time
import requests
import pandas as pd
import ast

# Setup
token = "2|cNxI00wYuPRjpO7N6N84dowZfybyXoaAn1y98nw76a3e656f"
base_url = "https://manager.crewcall.hu/api/"
headers = {"Authorization": f"Bearer {token}"}
output_dir = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/API_test"
template_path = os.path.join(output_dir, "export-2127-project-user-startforms.csv")  # must be manually placed here

os.makedirs(output_dir, exist_ok=True)

# Helper to fetch data from API
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

# Helper to flatten 'others' fields
def extract_others(row_val, label):
    result = {}
    try:
        entries = ast.literal_eval(row_val) if isinstance(row_val, str) else row_val
        if isinstance(entries, list):
            for i in range(min(2, len(entries))):
                item = entries[i] or {}
                result[f"{label} {i+1} description"] = item.get("name", "")
                result[f"{label} {i+1} price"] = item.get("price", "")
                result[f"{label} {i+1} account code"] = item.get("account_code", "")
    except Exception:
        pass
    return result

# Fetch API data
projects = fetch_data("project")
departments = fetch_data("department")
job_titles = fetch_data("job_title")
startforms = fetch_data("startform")

# Save raw data
pd.DataFrame(projects).to_csv(os.path.join(output_dir, "CrewManager_Projects.csv"), index=False)
pd.DataFrame(departments).to_csv(os.path.join(output_dir, "CrewManager_Departments.csv"), index=False)
pd.DataFrame(job_titles).to_csv(os.path.join(output_dir, "CrewManager_JobTitles.csv"), index=False)
pd.json_normalize(startforms).to_csv(os.path.join(output_dir, "CrewManager_StartForms.csv"), index=False)

# Lookups
project_lookup = {p["id"]: p["name"] for p in projects}
department_lookup = {d["id"]: d["name"] for d in departments}
job_title_lookup = {j["id"]: j["name"] for j in job_titles}

# Normalize SFs
df_sf = pd.json_normalize(startforms)

# Derived fields
df_sf["Sf number"] = df_sf["type"].fillna("") + df_sf["sf_number"].astype(str)
df_sf["Crew member id"] = df_sf["crew_member_id"].apply(lambda x: f"CM{int(x)}" if pd.notnull(x) else "")

# Human-readable mappings
df_sf["Project"] = df_sf["project_id"].map(project_lookup)
df_sf["Project department"] = df_sf["project_department_id"].map(department_lookup)
df_sf["Project job title"] = df_sf["project_job_title_id"].map(job_title_lookup)

# Placeholder user info
df_sf["User name"] = ""
df_sf["User surname"] = ""
df_sf["User email"] = ""
df_sf["User phone"] = ""

# Flatten others
df_daily = df_sf["daily_others"].apply(lambda x: pd.Series(extract_others(x, "Daily others")))
df_weekly = df_sf["weekly_others"].apply(lambda x: pd.Series(extract_others(x, "Weekly others")))
df_fee = df_sf["fee_others"].apply(lambda x: pd.Series(extract_others(x, "Fee others")))

# Add derived/flattened to DataFrame
df_combined = pd.concat([df_sf, df_daily, df_weekly, df_fee], axis=1)

# Load export template column structure
template_df = pd.read_csv(template_path)
final_columns = template_df.columns.tolist()

# Ensure all columns exist and are ordered correctly
for col in final_columns:
    if col not in df_combined.columns:
        df_combined[col] = ""

df_output = df_combined[final_columns]

# Export
output_file = os.path.join(output_dir, "Formatted_SFlist.csv")
df_output.to_csv(output_file, index=False)
print(f"✅ Final formatted SF list saved to: {output_file}")
