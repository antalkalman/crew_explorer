import streamlit as st
import pandas as pd
from datetime import datetime, time

st.set_page_config(page_title="DTS Submission", layout="wide")

st.title("🎬 Department Admin – Daily Time Sheet Entry")

# --- Sample data ----------------------------------
unit_schedule_data = [
    {"Date": "2025-05-27", "Unit": "Main Unit", "Workday": 10.0},
    {"Date": "2025-05-27", "Unit": "2nd Unit", "Workday": 12.0},
    {"Date": "2025-05-28", "Unit": "Main Unit", "Workday": 10.5},
    {"Date": "2025-05-28", "Unit": "Splinter", "Workday": 10.0},
    {"Date": "2025-05-29", "Unit": "Main Unit", "Workday": 10.0},
]
unit_schedule = pd.DataFrame(unit_schedule_data)

start_forms_data = [
    {"Name": "Tamás Bakos", "Title": "1st AC"},
    {"Name": "Tamás Forintos", "Title": "2nd AC"},
    {"Name": "Lilien Yang", "Title": "Camera Trainee"},
    {"Name": "Dániel Reich", "Title": "Camera Operator"},
    {"Name": "Dániel Benkő", "Title": "1st AC"},
    {"Name": "Attila Négyesy", "Title": "2nd AC"},
    {"Name": "Csenge Szabó", "Title": "Camera Trainee"},
    {"Name": "Jonatán Urbán", "Title": "Central Loader"},
    {"Name": "Declan O’Grianna", "Title": "A' Camera Operator"},
    {"Name": "David Radeker", "Title": "DOP"},
    {"Name": "Tamás Jánossa", "Title": "1st AC"},
    {"Name": "Bálint Ládi", "Title": "2nd AC"},
    {"Name": "Nándor Gulyás", "Title": "Camera Operator"},
]
start_forms = pd.DataFrame(start_forms_data)

# --- Selection ------------------------------------
unit_options = [
    f"{row['Date']} – {row['Unit']} ({row['Workday']}h)"
    for _, row in unit_schedule.iterrows()
]
selected_option = st.selectbox("Select Work Day and Unit", unit_options)
selected_date, unit_part = selected_option.split(" – ")
selected_unit = unit_part.split(" (")[0]
workday = unit_schedule.query("Date == @selected_date and Unit == @selected_unit")[["Workday"]].iloc[0, 0]

available_units = unit_schedule[unit_schedule["Date"] == selected_date]["Unit"].unique().tolist()
unit_choices = available_units + ["Off-Set", "Off-Set OT"]

st.markdown(f"📅 **Date:** {selected_date}  🎥 **Unit:** {selected_unit}  ⏱ **Workday Base:** {workday} hours")

# --- Defaults for Start / End ---
st.markdown("### 🔧 Default Start and End Time")
def_col1, def_col2 = st.columns([1, 1])
with def_col1:
    default_start = st.time_input("Default Start Time", value=time(8, 0))
with def_col2:
    default_end = st.time_input("Default End Time", value=time(17, 0))

# --- Entry table -----------------------------------
if "dts_rows" not in st.session_state:
    st.session_state.dts_rows = []

st.markdown("### 👥 Preloaded Crew from Start Forms")

# Header row
header = st.columns([3, 1, 1, 1, 1.5, 2.5, 3])
with header[0]: st.markdown("**Name – Title**")
with header[1]: st.markdown("**Worked**")
with header[2]: st.markdown("**Start**")
with header[3]: st.markdown("**End**")
with header[4]: st.markdown("**MP**")
with header[5]: st.markdown("**Unit**")
with header[6]: st.markdown("**Note**")

for crew in start_forms.to_dict(orient="records"):
    name_title = f"{crew['Name']} – {crew['Title']}"
    row = st.columns([3, 1, 1, 1, 1.5, 2.5, 3])
    with row[0]:
        st.markdown(f"**{name_title}**")
    with row[1]:
        worked = st.number_input("", min_value=0.0, step=0.5, value=1.0, key=f"worked_{crew['Name']}")
    with row[2]:
        start_time = st.time_input("", value=default_start, key=f"start_{crew['Name']}")
    with row[3]:
        end_time = st.time_input("", value=default_end, key=f"end_{crew['Name']}")
    with row[4]:
        mp = st.number_input("", min_value=0, step=1, value=0, key=f"mp_{crew['Name']}")
    with row[5]:
        unit_override = st.selectbox("", unit_choices, index=unit_choices.index(selected_unit), key=f"unit_{crew['Name']}")
    with row[6]:
        note = st.text_input("", key=f"note_{crew['Name']}")

    # Automatically add row when page is rendered (if not already added)
    if not any(r['Name'] == crew['Name'] for r in st.session_state.dts_rows):
        st.session_state.dts_rows.append({
            "Date": selected_date,
            "Name": crew['Name'],
            "Title": crew['Title'],
            "Worked": worked,
            "Start": start_time.strftime("%H:%M"),
            "End": end_time.strftime("%H:%M"),
            "Unit": unit_override,
            "MP": mp,
            "Note": note,
            "Manual": False
        })

# --- Table + Export -------------------------------
if st.session_state.dts_rows:
    st.markdown("### 📋 Current DTS Entries")
    dts_df = pd.DataFrame(st.session_state.dts_rows)
    st.dataframe(dts_df, use_container_width=True)

    csv = dts_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "💾 Export DTS as CSV",
        data=csv,
        file_name=f"DTS_{selected_date}_{selected_unit}.csv",
        mime="text/csv"
    )
