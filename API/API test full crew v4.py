import os
import time
import requests
import pandas as pd
import ast
import csv

# === CONFIG ===

# Automatically detect base directory
desktop_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/API_test"
laptop_path = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/API_test"

base_dir = desktop_path if os.path.exists(desktop_path) else laptop_path

# Token and API
token = "2|cNxI00wYuPRjpO7N6N84dowZfybyXoaAn1y98nw76a3e656f"
base_url = "https://manager.crewcall.hu/api/"
headers = {"Authorization": f"Bearer {token}"}

# File paths
mapping_file = os.path.join(base_dir, "export_field_mapping.xlsx")
output_file = os.path.join(base_dir, "Formatted_SFlist_Mapped.csv")

# Make sure folder exists
os.makedirs(base_dir, exist_ok=True)

# === FUNCTION: Fetch data from Crew Manager API ===
def fetch_data(endpoint, retries=3, delay=5):
    for attempt in range(retries):
        try:
            response = requests.get(
                url=f"{base_url}{endpoint}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} – Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise
    return None  # Explicit fallback

# === FETCH ALL API DATA ===
projects = fetch_data("project")
departments = fetch_data("department")
job_titles = fetch_data("job_title")
startforms = fetch_data("startform")

# === SAVE RAW SNAPSHOT FILES (OPTIONAL) ===
#pd.DataFrame(projects).to_csv(os.path.join(base_dir, "CrewManager_Projects.csv"), index=False)
#pd.DataFrame(departments).to_csv(os.path.join(base_dir, "CrewManager_Departments.csv"), index=False)
#pd.DataFrame(job_titles).to_csv(os.path.join(base_dir, "CrewManager_JobTitles.csv"), index=False)
#pd.json_normalize(startforms).to_csv(os.path.join(base_dir, "CrewManager_StartForms.csv"), index=False)

# === LOOKUPS BEFORE USING THEM ===
project_lookup = {p["id"]: p["name"] for p in projects}
department_lookup = {d["id"]: d["name"] for d in departments}
job_title_lookup = {j["id"]: j["name"] for j in job_titles}

# === LOAD AND NORMALIZE SF DATA ===
df_mapping = pd.read_excel(mapping_file)
df_sf = pd.json_normalize(startforms)

# Map readable values
df_sf["Project"] = df_sf["project_id"].map(project_lookup)
df_sf["Project department"] = df_sf["project_department_id"].map(department_lookup)
df_sf["Project job title"] = df_sf["project_job_title_id"].map(job_title_lookup)

# Clean up deal_notes
def clean_deal_note(val):
    if isinstance(val, str):
        return val.replace("\n", " ").replace("\r", " ").replace('"', '').replace(",", ";").strip()
    return val

if "deal_notes" in df_sf.columns:
    df_sf["deal_notes"] = df_sf["deal_notes"].apply(clean_deal_note)

# Derived fields
df_sf["Sf number"] = df_sf["type"].fillna("") + df_sf["sf_number"].astype(str)
df_sf["Crew member id"] = df_sf["crew_member_id"].apply(lambda x: f"CM{int(x)}" if pd.notnull(x) else "")

# === FLATTEN nested `others` fields ===
def extract_others(entry_list, label):
    result = {}
    try:
        if isinstance(entry_list, list):
            for i in range(min(2, len(entry_list))):
                item = entry_list[i] or {}
                result[f"{label} {i+1} description"] = str(item.get("name", "") or "")
                result[f"{label} {i+1} price"] = str(item.get("price", "") or "")
                result[f"{label} {i+1} account code"] = str(item.get("account_code", "") or "")
        else:
            parsed = ast.literal_eval(entry_list) if isinstance(entry_list, str) else []
            return extract_others(parsed, label)
    except Exception as e:
        result[f"{label} 1 description"] = f"⚠️ error: {e}"
    return result

# Apply flattening
df_daily = df_sf["daily_others"].apply(lambda x: pd.Series(extract_others(x, "Daily others")))
df_weekly = df_sf["weekly_others"].apply(lambda x: pd.Series(extract_others(x, "Weekly others")))
df_fee = df_sf["fee_others"].apply(lambda x: pd.Series(extract_others(x, "Fee others")))

# Combine all flattened columns
df_sf = pd.concat([df_sf, df_daily, df_weekly, df_fee], axis=1)

# === BUILD FINAL OUTPUT ===
output_dict = {}

for _, row in df_mapping.iterrows():
    export_col = row["Export Column (Official)"]
    api_field = row["API Field (from CrewManager_StartForms.csv)"]

    if export_col in df_sf.columns and (pd.isna(api_field) or api_field.strip() == ""):
        output_dict[export_col] = df_sf[export_col]
    elif pd.isna(api_field) or api_field.strip() == "":
        output_dict[export_col] = ""
    elif " + " in api_field:
        try:
            parts = [df_sf[p.strip()] if p.strip() in df_sf.columns else "" for p in api_field.split("+")]
            output_dict[export_col] = parts[0].astype(str) + parts[1].astype(str)
        except Exception:
            output_dict[export_col] = ""
    elif api_field.startswith('"CM" +'):
        field = api_field.split("+")[1].strip()
        output_dict[export_col] = df_sf[field].apply(lambda x: f"CM{int(x)}" if pd.notnull(x) else "")
    elif api_field in df_sf.columns:
        output_dict[export_col] = df_sf[api_field]
    else:
        output_dict[export_col] = ""

output_data = pd.DataFrame(output_dict)

# === EXPORT CSV WITH QUOTING ===
output_data.to_csv(output_file, index=False, quoting=csv.QUOTE_ALL)
print(f"✅ Final formatted export saved to:\n{output_file}")
