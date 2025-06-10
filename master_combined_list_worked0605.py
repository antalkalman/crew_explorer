import os
import pandas as pd
from glob import glob

# === Folder Setup ===
desktop_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database"
laptop_path = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database"
base_dir = desktop_path if os.path.exists(desktop_path) else laptop_path

# === Locate latest Historical file ===
historical_pattern = os.path.join(base_dir, "Historical_data_*.xlsx")
historical_files = glob(historical_pattern)
if not historical_files:
    print("❌ No historical data files found.")
    exit()

historical_path = max(historical_files, key=os.path.getmtime)
print(f"📄 Using historical file: {os.path.basename(historical_path)}")

# === Load data ===
df = pd.read_excel(historical_path, engine="openpyxl")
df.columns = df.columns.str.strip()

# === Filter out rows with no 'Crew list name' ===
df = df[df["Crew list name"].notna() & (df["Crew list name"].astype(str).str.strip() != "")]

# === Build output with specified column order ===
columns_out = [
    "GCMID",
    "Crew list name",
    "General Title",
    "Mobile number",
    "Email",
    "Project",                    # ← Newly inserted here
    "Project department",
    "Project job title",
    "Company: Company name / Cégnév",
    "Surname",
    "Firstname",
    "Nickname",
    "CM ID",
    "User name",
    "User surname",
    "User email",
    "User phone",
    "business_type"
]


# Build dataframe with strict column order, defaulting to empty if missing
df_out = pd.DataFrame()
for col in columns_out:
    if col == "CM ID":
        df_out[col] = df.get("Crew member id", "")
    elif col == "Company: Company name / Cégnév":
        df_out["Company"] = df.get(col, "")
    else:
        df_out[col] = df.get(col, "")


# Rename the long company field
df_out = df_out.rename(columns={"Company: Company name / Cégnév": "Company"})

# Add source column
df_out["Source"] = "Historical"



# === Export ===
output_path = os.path.join(base_dir, "debug_historical_only.xlsx")
df_out.to_excel(output_path, index=False)
print(f"✅ Exported to: {output_path}")
