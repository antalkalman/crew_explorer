import os
import glob
import pandas as pd

# === SET BASE DIRECTORY ===
desktop_base = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database"
laptop_base = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database"
base_dir = desktop_base if os.path.exists(desktop_base) else laptop_base

# === FILE PATHS ===
mapping_file = os.path.join(base_dir, "combined_field_mapping.xlsx")
names_file = os.path.join(base_dir, "Names.xlsx")
sflist_pattern = os.path.join(base_dir, "SFlist_*.csv")
history_pattern = os.path.join(base_dir, "Historical_data_*.xlsx")
output_path = os.path.join(base_dir, "Combined_All_CrewData.xlsx")
helper_file = os.path.join(base_dir, "Helper.xlsx")

# === LOAD MAPPING AND FINAL FIELD LIST ===
mapping_df = pd.read_excel(mapping_file)
final_fields = mapping_df['Final Field Names'].dropna().unique().tolist()

map_hist = mapping_df.set_index('History Field Names')['Final Field Names'].dropna().to_dict()
map_sf = mapping_df.set_index('Sflist Field Names')['Final Field Names'].dropna().to_dict()
map_names = mapping_df.set_index('Names Field Names')['Final Field Names'].dropna().to_dict()


# === REPLACE YOUR OLD standardize() FUNCTION WITH THIS ===
def standardize(df, mapping, origin_label):
    df_mapped = df.rename(columns=mapping).copy()
    missing_cols = [col for col in final_fields if col not in df_mapped.columns]
    df_mapped = df_mapped.assign(**{col: "" for col in missing_cols})
    df_mapped = df_mapped.reindex(columns=final_fields)  # Ensure consistent order
    df_mapped["Origin"] = origin_label
    return df_mapped

# === LOAD RAW DATA SOURCES ===
sflist_file = sorted(glob.glob(sflist_pattern), reverse=True)[0]
history_file = sorted(glob.glob(history_pattern), reverse=True)[0]

df_sflist = pd.read_csv(sflist_file, dtype=str)
df_history = pd.read_excel(history_file, dtype=str)
df_names_raw = pd.read_excel(names_file, sheet_name="Names")
df_names_map = df_names_raw.copy()

# === STANDARDIZE ALL DATASETS ===
df_hist_std = standardize(df_history, map_hist, "Historical")
df_sf_std = standardize(df_sflist, map_sf, "SFlist")
df_names_std = standardize(df_names_raw, map_names, "Names")

# ... your code up to df_names_std = standardize(...)

# === POST-FILL FOR "Names" ORIGIN ONLY ===
mask_names = df_names_std["Origin"] == "Names"
df_names_std.loc[mask_names, "Surname"] = df_names_map["Sure Name"]
df_names_std.loc[mask_names, "Firstname"] = df_names_map["First Name"]
df_names_std.loc[mask_names, "Nickname"] = df_names_map["Nick Name"]
df_names_std.loc[mask_names, "Mobile number"] = df_names_map["Actual Phone"]
df_names_std.loc[mask_names, "Email"] = df_names_map["Actual Email"]
df_names_std.loc[mask_names, "Project"] = "Phone Book"



def build_crew_list_name(row):
    fn = str(row.get("First Name") or "").strip()
    sn = str(row.get("Sure Name") or "").strip()
    nick = str(row.get("Nick Name") or "").strip()
    name = f"{fn} {sn}".strip()
    if nick and nick.lower() != "nan":
        name += f' {nick}'
    return name.strip()

df_names_std.loc[mask_names, "Crew list name"] = df_names_map.apply(build_crew_list_name, axis=1)
df_names_std.loc[mask_names, "Actual Name"] = df_names_std.loc[mask_names, "Crew list name"]

# === GCMID mapping for SFlist ===
df_gcmid_map = pd.read_excel(helper_file, sheet_name="GCMID", dtype=str)
df_gcmid_map["CM-Job"] = df_gcmid_map["CM-Job"].astype(str).str.strip()

# Create "CM--Project" field for SFlist
df_sf_std["CM--Project"] = (
    df_sf_std["Crew member id"].fillna("") + "--" + df_sf_std["Project"].fillna("")
).str.strip()

df_hist_std["GCMID"] = df_hist_std["GCMID"].astype(str)
df_sf_std["GCMID"] = df_sf_std["GCMID"].astype(str)
df_names_map["CM ID"] = df_names_map["CM ID"].astype(str)

# Ensure "Project--Title" field is filled for SFlist
df_sf_std["Project--Title"] = (
    df_sf_std["Project"].fillna("") + "--" + df_sf_std["Project job title"].fillna("")
).str.strip()

# === General Title Mapping from Helper ===
df_titleconv = pd.read_excel(helper_file, sheet_name="Title conv", dtype=str)
title_project_to_general = df_titleconv.set_index("Title-Project")["General Title"].to_dict()

# Fill General Title using 'Title-Project' field
df_sf_std["General Title"] = df_sf_std["Title-Project"].map(title_project_to_general)
df_hist_std["General Title"] = df_hist_std["Title-Project"].map(title_project_to_general)


# Map CM--Project to GCMID
cmjob_to_gcmid = df_gcmid_map.set_index("CM-Job")["CM ID"].to_dict()
df_sf_std["GCMID"] = df_sf_std["CM--Project"].map(cmjob_to_gcmid)

# === Compute 'Actual Name' in df_names_map ===
df_names_map["Actual Name"] = df_names_map.apply(build_crew_list_name, axis=1)

# === Create lookup based on GCMID ===
lookup_fields = ["Actual Name", "Actual Title", "Actual Phone", "Actual Email", "Note"]
name_lookup = df_names_map.set_index("CM ID")[lookup_fields].to_dict(orient="index")

# === Fill Historical and SFlist records using GCMID ===
def fill_actual_fields(row):
    gcmid = row.get("GCMID")
    if pd.notna(gcmid) and gcmid in name_lookup:
        for field in lookup_fields:
            row[field] = name_lookup[gcmid].get(field, "")
    return row

df_hist_std = df_hist_std.apply(fill_actual_fields, axis=1)
df_sf_std = df_sf_std.apply(fill_actual_fields, axis=1)



# === FINAL COMBINE ===
df_all = pd.concat([df_hist_std, df_sf_std, df_names_std], ignore_index=True)

# === Load General Title mapping from Helper.xlsx ===
df_title_map = pd.read_excel(helper_file, sheet_name="General Title", dtype=str)

# Build a dictionary keyed by 'Title'
title_lookup = df_title_map.set_index("Title")[["Department", "Department ID", "Title ID"]].to_dict(orient="index")

# Apply mapping to df_all
for idx, row in df_all.iterrows():
    title = row.get("General Title", "")
    if title in title_lookup:
        mapping = title_lookup[title]
        df_all.at[idx, "General Department"] = mapping.get("Department", "")
        df_all.at[idx, "Department ID"] = mapping.get("Department ID", "")
        df_all.at[idx, "Title ID"] = mapping.get("Title ID", "")

# === Load FProjects for mapping ===
df_projects = pd.read_excel(helper_file, sheet_name="FProjects", dtype=str)
project_to_start = df_projects.set_index("Project")["Start date"].to_dict()
project_to_end = df_projects.set_index("Project")["End date"].to_dict()

# === Fill directly via map (preserves column order, avoids _x/_y) ===
df_all["Project start date"] = df_all["Project"].map(project_to_start).fillna(df_all["Project start date"])
df_all["Project end date"] = df_all["Project"].map(project_to_end).fillna(df_all["Project end date"])




# === EXPORT TO EXCEL ===
df_all.to_excel(output_path, index=False)
print(f"✅ Combined file saved to: {output_path}")
