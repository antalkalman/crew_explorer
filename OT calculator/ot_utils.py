import streamlit as st
from datetime import datetime
import math

st.set_page_config(layout="wide")
st.title("🧪 OT & TA Calculation Playground (Manual Mode)")

st.subheader("📝 Input Times")

# --- Free text input for times ---
col1, col2, col3 = st.columns(3)
start_input = col1.text_input("Start Time (e.g. 6:30)", value="6:30")
end_input = col2.text_input("End Time (e.g. 20:15)", value="20:15")
working_day = col3.number_input("Working Day (hours)", value=12.0, min_value=0.0, step=0.5)

# --- Manual OT rules ---
st.subheader("⚙️ OT Settings")
col4, col5, col6 = st.columns(3)
rounding_min = col4.number_input("Rounding period (minutes)", value=60, min_value=1)
grace_first = col5.number_input("Grace in 1st hour (minutes)", value=15, min_value=0)
grace_other = col6.number_input("Grace in other hours (minutes)", value=5, min_value=0)

# --- Parse and validate times ---
try:
    start_time = datetime.strptime(start_input.strip(), "%H:%M")
    end_time = datetime.strptime(end_input.strip(), "%H:%M")

    if end_time < start_time:
        end_time = end_time.replace(day=end_time.day + 1)  # handle overnight

    worked_hours = (end_time - start_time).total_seconds() / 3600
    ot_raw_minutes = max(0, (worked_hours - working_day) * 60)

    if ot_raw_minutes <= 0:
        ot_final_minutes = 0
    else:
        full_periods = ot_raw_minutes // rounding_min
        remainder = ot_raw_minutes % rounding_min

        if ot_raw_minutes < rounding_min:
            # Still in first period → use first grace
            grace = grace_first
        else:
            # Past first period → use other grace
            grace = grace_other

        if remainder <= grace:
            ot_final_minutes = full_periods * rounding_min  # round down
        else:
            ot_final_minutes = (full_periods + 1) * rounding_min  # round up

    # Output
    st.subheader("📊 Results")
    col7, col8 = st.columns(2)
    col7.metric("OT hours (raw)", f"{ot_raw_minutes / 60:.2f}")
    col8.metric("Rounded OT", f"{ot_final_minutes / 60:.2f}")

except ValueError:
    st.error("❌ Please enter valid time formats like 6:30 or 20:15")
