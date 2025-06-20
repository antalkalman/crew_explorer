import streamlit as st
import pandas as pd
import os

# === Load Data ===
file_paths = [
    "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/visual_test/data_for_visual_test.xlsx",
    "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/visual_test/data_for_visual_test.xlsx"
]

for path in file_paths:
    if os.path.exists(path):
        data_path = path
        break
else:
    st.error("❌ Could not find Excel file.")
    st.stop()

df = pd.read_excel(data_path)
df["Date"] = pd.to_datetime(df["Date"])
df["Status"] = df["Status"].fillna("")

# === UI Setup ===
st.set_page_config(layout="wide")
st.title("📝 Approve Daily Time Sheets by Department")

# --- Date Selection ---
available_dates = sorted(df["Date"].dt.date.unique())
selected_date = st.selectbox("📅 Select Date to Review", available_dates)

# --- Filter by selected date ---
filtered_df = df[df["Date"].dt.date == selected_date].copy()

# Make a working copy for edits across departments
edited_df = df.copy()

# Define status options and display labels
status_options = ["Prepped", "Approved", "Signed", "Correct", ""]
status_labels = {
    "Prepped": "Prepped",
    "Approved": "Approved",
    "Signed": "Signed",
    "Correct": "Correct",
    "": "⛔ Empty"
}

# === Loop through Departments ===
for dept in filtered_df["Department"].dropna().unique():
    st.subheader(f"📦 Department: {dept}")

    dept_df = filtered_df[filtered_df["Department"] == dept].copy()

    default_status = st.radio(
        f"✅ Select new status for {dept}",
        options=status_options,
        format_func=lambda x: status_labels[x],
        horizontal=True,
        key=f"radio_{dept}"
    )

    st.markdown("### ⛔ Exclude or Review Rows (Checked rows will not be updated)")

    excluded_ids = []
    for _, row in dept_df.iterrows():
        cols = st.columns([0.3, 0.8, 0.6, 0.6, 0.5, 1])
        with cols[0]:
            exclude = st.checkbox("", key=f"exclude_{row['ID']}")
            if exclude:
                excluded_ids.append(row["ID"])

        with cols[1]:
            st.markdown(f"**{row['Name']}** – {row['Title']}")

        with cols[2]:
            start = row["Start"].strftime("%H:%M") if pd.notnull(row["Start"]) else ""
            st.markdown(f"Start: `{start}`")

        with cols[3]:
            end = row["End"].strftime("%H:%M") if pd.notnull(row["End"]) else ""
            st.markdown(f"End: `{end}`")

        with cols[4]:
            ot = f"{int(row['OT'])}" if pd.notnull(row["OT"]) else ""
            st.markdown(f"OT: `{ot}`")

        with cols[5]:
            status = row["Status"]
            color_map = {
                "Prepped": "gray",
                "Approved": "green",
                "Signed": "blue",
                "Correct": "orange",
                "": "red"
            }
            color = color_map.get(status, "black")
            st.markdown(
                f"<span style='color:{color}; font-weight:bold;'> {status or 'Empty'}</span>",
                unsafe_allow_html=True
            )

    if st.button(f"📌 Apply '{default_status}' to all in {dept}", key=f"apply_{dept}"):
        ids_to_update = dept_df[~dept_df["ID"].isin(excluded_ids)]["ID"].tolist()
        df.loc[df["ID"].isin(ids_to_update), "Status"] = default_status
        st.success(f"✅ Updated {len(ids_to_update)} records in {dept}.")


# Optional CSV export
st.download_button(
    "💾 Download Updated Data",
    data=df.to_csv(index=False),
    file_name=f"TS_Status_Updated_{selected_date}.csv",
    mime="text/csv"
)
