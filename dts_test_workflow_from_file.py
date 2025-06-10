import streamlit as st
import pandas as pd
from datetime import datetime, time

st.set_page_config(page_title="DTS Entry – Core Crew", layout="wide")


# Load Excel files
sf_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/DTS test/Dummy_SFs.xlsx"
wd_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/DTS test/Dummy_Working_Days.xlsx"

sf_df = pd.read_excel(sf_path)
wd_df = pd.read_excel(wd_path)

#st.write(sf_df.columns.tolist())


# Filter core crew only
core_crew_df = sf_df[sf_df["core_daily"].str.lower() == "core crew"].copy()

# UI layout
st.title("🎬 Daily Time Sheet Entry – Core Crew Only")

# Select Date + Unit
wd_df["Label"] = wd_df["Date"].astype(str) + " – " + wd_df["Unit"]
selected_label = st.selectbox("Select Date and Unit", wd_df["Label"])
selected_row = wd_df[wd_df["Label"] == selected_label].iloc[0]
selected_date = selected_row["Date"]
selected_unit = selected_row["Unit"]
working_hours = selected_row["Workinhg Hours"]  # spelling from Excel

# Show header
st.markdown(f"📅 **Date:** {selected_date} 🎥 **Unit:** {selected_unit} ⏱ **Base Workday:** {working_hours}h")

# Defaults
default_start = time(8, 0)
default_end = time(17, 0)

# Show DTS input table
st.markdown("### 👥 Core Crew – Daily Time Sheet")
header = st.columns([3, 1, 1, 1, 1, 2, 3])
with header[0]: st.markdown("**Name – Title**")
with header[1]: st.markdown("**Worked**")
with header[2]: st.markdown("**Start**")
with header[3]: st.markdown("**End**")
with header[4]: st.markdown("**MP**")
with header[5]: st.markdown("**Unit**")
with header[6]: st.markdown("**Note**")

# Build and render input rows
dts_entries = []
for i, row in core_crew_df.iterrows():
    name_title = f"{row['Name']} – {row['Title']}"
    cols = st.columns([3, 1, 1, 1, 1, 2, 3])

    with cols[0]:
        st.text_input("", value=name_title, key=f"debug_name_{i}")
    with cols[1]:
        worked = st.number_input("", min_value=0.0, step=0.5, value=1.0, format="%.2f", key=f"worked_{i}")
    with cols[2]:
        start = st.time_input("", value=default_start, key=f"start_{i}")
    with cols[3]:
        end = st.time_input("", value=default_end, key=f"end_{i}")
    with cols[4]:
        mp = st.number_input("", min_value=0, step=1, value=0, key=f"mp_{i}")
    with cols[5]:
        unit_override = st.selectbox("", [selected_unit, "Off-Set", "Off-Set OT"], key=f"unit_{i}")
    with cols[6]:
        note = st.text_input("", key=f"note_{i}")

    dts_entries.append({
        "Date": selected_date,
        "Name": row["Name"],
        "Title": row["Title"],
        "Worked": worked,
        "Start": start.strftime("%H:%M"),
        "End": end.strftime("%H:%M"),
        "MP": mp,
        "Unit": unit_override,
        "Note": note
    })

# Export block
if dts_entries:
    st.markdown("### 📤 Export Daily TS")
    export_df = pd.DataFrame(dts_entries)
    st.dataframe(export_df, use_container_width=True)

    csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("💾 Download CSV", data=csv, file_name=f"DTS_{selected_date}_{selected_unit}.csv", mime="text/csv")
