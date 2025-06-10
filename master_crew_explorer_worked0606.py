import os
import pandas as pd
import streamlit as st
from datetime import datetime

# === Detect path ===
desktop_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database/Combined_Crew_Master.xlsx"
laptop_path = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database/Combined_Crew_Master.xlsx"
excel_path = desktop_path if os.path.exists(desktop_path) else laptop_path

# === Load data ===
@st.cache_data
@st.cache_data
def load_data():
    df = pd.read_excel(excel_path)
    df["Project start date"] = pd.to_datetime(df["Project start date"], origin='1899-12-30', unit='D', errors="coerce")
    df["Project end date"] = pd.to_datetime(df["Project end date"], origin='1899-12-30', unit='D', errors="coerce")

    # Sort by Project start date, Department ID, Title ID
    df = df.sort_values(by=["Project start date", "Department ID", "Title ID"], ascending=[False, True, True])

    # Format phone numbers
    phone_cols = ["Actual Phone", "Mobile number", "User phone"]
    for col in phone_cols:
        if col in df.columns:
            df[col] = df[col].apply(format_hu_phone)

    return df

def format_hu_phone(number):
    try:
        num = str(int(float(number)))  # handles floats like 3.630971e+10
        if num.startswith("36") and len(num) == 11:
            return f"+36 {num[2:4]} {num[4:7]} {num[7:]}"
        elif num.startswith("06") and len(num) == 11:
            return f"+36 {num[2:4]} {num[4:7]} {num[7:]}"
        elif num.startswith("30") and len(num) == 9:
            return f"+36 {num[:2]} {num[2:5]} {num[5:]}"
        else:
            return number
    except:
        return number


df = load_data()

st.sidebar.header("🔍 Crew Explorer Filters")

# Running Projects toggle (placed first)
active_only = st.sidebar.checkbox("📅 Only Running Projects", value=True)

# Filter project options accordingly
today = pd.to_datetime("today")
if active_only:
    project_options = df[df["Project end date"] >= today]["Project"].dropna().unique()
else:
    project_options = df["Project"].dropna().unique()

project_filter = st.sidebar.multiselect("🎬 Project", sorted(project_options))

# Name Filter
name_filter = st.sidebar.text_input("🔤 Name contains...")

# Department → affects Title
gen_dept_options = sorted(df["General Department"].dropna().unique())
gen_dept_filter = st.sidebar.multiselect("🏷️ General Department", gen_dept_options)

# Dependent Title Dropdown
if gen_dept_filter:
    available_titles = df[df["General Department"].isin(gen_dept_filter)]["General Title"].dropna().unique()
else:
    available_titles = df["General Title"].dropna().unique()
gen_title_filter = st.sidebar.multiselect("🎓 General Title", sorted(available_titles))


# === SMART Filter logic ===
filtered_df = df.copy()
mask_list = []

# Group: Name
if name_filter:
    mask_list.append(filtered_df["Crew list name"].str.contains(name_filter, case=False, na=False))

# Group: General Department
if gen_dept_filter:
    mask_list.append(filtered_df["General Department"].isin(gen_dept_filter))

# Group: General Title
if gen_title_filter:
    mask_list.append(filtered_df["General Title"].isin(gen_title_filter))

# Group: Project
if project_filter:
    mask_list.append(filtered_df["Project"].isin(project_filter))

# Group: Running Projects
if active_only:
    today = pd.to_datetime("today")
    mask_list.append(filtered_df["Project end date"] >= today)

# Combine across groups (AND)
for m in mask_list:
    filtered_df = filtered_df[m]


# Format dates for display
filtered_df["Project start date"] = filtered_df["Project start date"].dt.strftime("%Y.%m.%d.")
filtered_df["Project end date"] = filtered_df["Project end date"].dt.strftime("%Y.%m.%d.")

# === View mode selector ===
view_mode = st.radio(
    "👁️ Choose column view:",
    ["🟢 General", "🔵 On Project", "⚙️ Full"],
    horizontal=True
)

# === Daily Fee toggle ===
show_fee = st.checkbox("💰 Show Daily Fee", value=False)

general_cols = [
    "Actual Name", "General Department", "Actual Title",
    "Actual Phone", "Actual Email", "Project", "GCMID", "Source"
]

project_cols = [
    "Crew list name", "Project department", "Project job title",
    "Mobile number", "Email", "Project", "GCMID", "Source"
]

full_cols = list(filtered_df.columns)

# Choose base columns
if view_mode == "🟢 General":
    selected_cols = general_cols
elif view_mode == "🔵 On Project":
    selected_cols = project_cols
else:
    selected_cols = full_cols

# Add Daily Fee column if toggle is ON and it exists
if show_fee and "Daily fee" in filtered_df.columns:
    if "Daily fee" not in selected_cols:
        selected_cols.append("Daily fee")
else:
    # Remove Daily fee if it's off
    selected_cols = [col for col in selected_cols if col != "Daily fee"]


# === Display result ===
st.title("🎬 Crew Explorer")
st.markdown(f"Showing **{len(filtered_df)}** matching crew member(s)")

# Make a display copy so formatting doesn’t affect the original DataFrame
display_df = filtered_df.copy()

if "Daily fee" in display_df.columns and show_fee:
    display_df["Daily fee"] = display_df["Daily fee"].apply(
        lambda x: f"{int(x):,}".replace(",", " ") if pd.notnull(x) else ""
    )


#st.dataframe(filtered_df, use_container_width=True)
st.dataframe(display_df[selected_cols], use_container_width=True)


# === Export option ===
st.download_button(
    "⬇️ Download Filtered CSV",
    filtered_df.to_csv(index=False).encode("utf-8"),
    "filtered_crew_export.csv",
    "text/csv"
)
