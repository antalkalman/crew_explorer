import os
import pandas as pd
import streamlit as st
import re
import unicodedata
from datetime import datetime

st.set_page_config(layout="wide")

from datetime import datetime
today = pd.Timestamp(datetime.today().date())


# === Name normalizer (global function) ===
def normalize(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")  # strip accents
    text = re.sub(r"[^a-z0-9]", "", text)  # remove non-alphanumeric
    return text

import os

# === Detect path ===
local_filename = "Combined_All_CrewData.xlsx"
excel_path = os.path.join(os.path.dirname(__file__), local_filename)


# === Load data ===
@st.cache_data
# === Load data ===
@st.cache_data
def load_data():
    df = pd.read_excel(excel_path)
    return df


    # === Convert Excel serial dates ===
    date_cols = ["Project start date", "Project end date"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], origin='1899-12-30', unit='D', errors='coerce')

    # === Format Hungarian phone numbers ===
    def format_hu_phone(number):
        try:
            num = str(int(float(number)))  # handles scientific notation
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

    phone_cols = ["Actual Phone", "Mobile number", "User phone"]
    for col in phone_cols:
        if col in df.columns:
            df[col] = df[col].apply(format_hu_phone)

    # === Sort by start date, dept, title ===
    for col in ["Department ID", "Title ID"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(
        by=["Project start date", "Department ID", "Title ID"],
        ascending=[False, True, True]
    )

    df["search_name"] = df["Crew list name"].apply(normalize)

    return df

df = load_data()

st.sidebar.header("🔍 Crew Explorer Filters")

# Running Projects toggle (placed first)
active_only = st.sidebar.checkbox("📅 Only Running Projects", value=True)

# Filter project options accordingly
today = pd.to_datetime("today")
if active_only:
    df["Project end date"] = pd.to_datetime(df["Project end date"], errors="coerce")
    project_df = df[df["Project end date"] >= today][["Project", "Project start date"]]
else:
    project_df = df[["Project", "Project start date"]]

project_df = project_df.dropna().drop_duplicates().sort_values("Project start date", ascending=False)
project_options = project_df["Project"].tolist()

project_filter = st.sidebar.multiselect("🎬 Project", project_options)

origin_options = sorted(df["Origin"].dropna().unique())
origin_filter = st.sidebar.multiselect("🌍 Origin", origin_options)




# Department → affects Title
# Sort departments by Department ID
dept_df = df[["General Department", "Department ID"]].dropna().drop_duplicates()
dept_df = dept_df.sort_values("Department ID")
gen_dept_options = dept_df["General Department"].tolist()
gen_dept_filter = st.sidebar.multiselect("🏷️ General Department", gen_dept_options)

# Dependent Title Dropdown
if gen_dept_filter:
    title_df = df[df["General Department"].isin(gen_dept_filter)][["General Title", "Title ID"]]
else:
    title_df = df[["General Title", "Title ID"]]

title_df = title_df.dropna().drop_duplicates().sort_values("Title ID")
available_titles = title_df["General Title"].tolist()

gen_title_filter = st.sidebar.multiselect("🎓 General Title", available_titles)

# Name Filter
name_filter = st.sidebar.text_input("🔤 Name contains...")


# === SMART Filter logic ===
filtered_df = df.copy()
mask_list = []

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

# Group: Origin
if origin_filter:
    mask_list.append(filtered_df["Origin"].isin(origin_filter))


# Combine across groups (AND)
for m in mask_list:
    filtered_df = filtered_df[m]

# === Then: apply Name as a "search" not filter ===
if name_filter:
    name_norm = normalize(name_filter)
    matched_gcmids = df[df["search_name"].str.contains(name_norm, na=False)]["GCMID"].unique()
    filtered_df = filtered_df[filtered_df["GCMID"].isin(matched_gcmids)]

# Make sure both date columns are in datetime format
filtered_df["Project start date"] = pd.to_datetime(filtered_df["Project start date"], errors="coerce")
filtered_df["Project end date"] = pd.to_datetime(filtered_df["Project end date"], errors="coerce")

# Format both as "YYYY.MM.DD." and handle missing values
filtered_df["Project start date"] = filtered_df["Project start date"].dt.strftime("%Y.%m.%d.")
filtered_df["Project end date"] = filtered_df["Project end date"].dt.strftime("%Y.%m.%d.")

# Fill NaT (missing) entries with empty string
filtered_df["Project start date"] = filtered_df["Project start date"].fillna("")
filtered_df["Project end date"] = filtered_df["Project end date"].fillna("")


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
    "Actual Phone", "Actual Email", "Project", "GCMID", "Origin"
]

project_cols = [
    "Crew list name", "Project department", "Project job title",
    "Mobile number", "Crew email", "Project", "GCMID", "Origin"
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
