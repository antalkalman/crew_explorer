import os
import re
import pandas as pd
from datetime import datetime

# === Set folder where SF_Archive lives ===
desktop_archive = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/SF_Archive"
laptop_archive = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/SF_Archive"
archive_dir = desktop_archive if os.path.exists(desktop_archive) else laptop_archive

# === Match SFlist_YYYYMMDD_HHMM.csv filenames ===
pattern = re.compile(r"SFlist_(\d{8}_\d{4})\.csv$")
sf_files = []

for f in os.listdir(archive_dir):
    match = pattern.match(f)
    if match:
        try:
            ts = datetime.strptime(match.group(1), "%Y%m%d_%H%M")
            sf_files.append((ts, f))
        except ValueError:
            continue

if len(sf_files) < 2:
    raise FileNotFoundError("❌ Need at least two SFlist_YYYYMMDD_HHMM.csv files in the 'SF_Archive' folder.")

# Sort descending by timestamp
sf_files.sort(reverse=True)
latest_file = sf_files[0][1]
older_file = sf_files[1][1]

print(f"🔍 Comparing:\n  NEW : {latest_file}\n  OLD : {older_file}")

# === Load CSVs ===
sf_list = pd.read_csv(os.path.join(archive_dir, latest_file), dtype=str).fillna("")
af_list_old = pd.read_csv(os.path.join(archive_dir, older_file), dtype=str).fillna("")

# === Load compare_directions.xlsx ===
directions_path = os.path.join(archive_dir, "compare_directions.xlsx")
df_directions = pd.read_excel(directions_path)
df_directions.columns = [col.strip() for col in df_directions.columns[:2]]
field_to_category = dict(zip(df_directions.iloc[:, 0].astype(str).str.strip(), df_directions.iloc[:, 1].astype(str).str.strip()))

# === Normalize ===
def normalize(df):
    return df.applymap(lambda x: x.strip().lower() if isinstance(x, str) else x)

sf_clean = normalize(sf_list)
af_clean = normalize(af_list_old)
af_dict = af_clean.set_index("ID").to_dict(orient="index")

# === Compare rows ===
def compare_row(row):
    row_id = row["ID"]
    if row_id not in af_dict:
        return "new"
    old_row = af_dict[row_id]
    diffs = []
    for col in sf_clean.columns:
        category = field_to_category.get(col, "")
        if col == "ID" or category in {"skip", "del"}:
            continue
        if row[col] != old_row.get(col, ""):
            diffs.append(col)
    return ", ".join(diffs) if diffs else "unchanged"

sf_clean["Change Status"] = sf_clean.apply(compare_row, axis=1)

# === Merge results with original data ===
output = sf_list.copy()
output["Change Status"] = sf_clean["Change Status"]

# === Add Category column ===
def get_primary_category(change_str):
    if change_str in ("", "unchanged", "new"):
        return ""
    first_field = change_str.split(",")[0].strip()
    return field_to_category.get(first_field, "")

output["Category"] = output["Change Status"].apply(get_primary_category)
output.loc[output["Change Status"] == "unchanged", "Category"] = "unchanged"
output.loc[output["Change Status"] == "new", "Category"] = "new"

# === Drop fields marked as 'del' ===
del_fields = [field for field, cat in field_to_category.items() if cat == "del"]
columns_to_keep = [col for col in output.columns if col not in del_fields]
output = output[columns_to_keep]

# === Filter out 'unchanged' rows ===
output = output[output["Change Status"] != "unchanged"].copy()

# === Final CSV export to Temp folder ===
temp_dir = os.path.join(archive_dir, "Temp")
os.makedirs(temp_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
csv_filename = f"SFlist_changes_{timestamp}.csv"
csv_path = os.path.join(temp_dir, csv_filename)

# === Reorder columns: Category first, then Change Status ===
cols = output.columns.tolist()
cols.remove("Category")
cols.remove("Change Status")
output = output[["Category", "Change Status"] + cols]

output.to_csv(csv_path, index=False)
print(f"📄 CSV saved to Temp folder:\n{csv_path}")
