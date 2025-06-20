import streamlit as st
import pandas as pd

# 👉 Enable wide mode
st.set_page_config(layout="wide")

# --- Load and Clean Data ---
df = pd.read_excel("/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/visual_test/data_for_visual_test.xlsx")
df.columns = df.columns.str.strip()
df["Date"] = pd.to_datetime(df["Date"])

# --- Initialize Approval Memory (by ID) ---
if "approved_ids" not in st.session_state:
    st.session_state["approved_ids"] = set()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

unit_options = sorted(df["Unit"].dropna().unique())
dept_options = sorted(df["Department"].dropna().unique())
date_options = sorted(df["Date"].dt.date.unique())
id_options = sorted(df["ID"].dropna().unique())

unit_filter = st.sidebar.multiselect("Select Unit(s)", ["All"] + unit_options, default=["All"])
if "All" in unit_filter or not unit_filter:
    unit_filter = unit_options

department_filter = st.sidebar.multiselect("Select Department(s)", ["All"] + dept_options, default=["All"])
if "All" in department_filter or not department_filter:
    department_filter = dept_options

date_filter = st.sidebar.multiselect("Select Date(s)", ["All"] + date_options, default=["All"])
if "All" in date_filter or not date_filter:
    date_filter = date_options

id_filter = st.sidebar.multiselect("Select ID(s)", ["All"] + id_options, default=["All"])
if "All" in id_filter or not id_filter:
    id_filter = id_options

# --- Top Filter: Approval Status ---
status_filter = st.radio("Approval Status", ["All", "Approved", "Unapproved"], horizontal=True)

# --- Filter DataFrame ---
filtered_df = df[
    (df["Unit"].isin(unit_filter)) &
    (df["Department"].isin(department_filter)) &
    (df["Date"].dt.date.isin(date_filter)) &
    (df["ID"].isin(id_filter))
]

if status_filter == "Approved":
    filtered_df = filtered_df[filtered_df["ID"].isin(st.session_state["approved_ids"])]
elif status_filter == "Unapproved":
    filtered_df = filtered_df[~filtered_df["ID"].isin(st.session_state["approved_ids"])]

# --- Action Buttons ---
col1, col2 = st.columns(2)
if col1.button("✅ Approve All Visible"):
    ids = filtered_df["ID"].dropna().tolist()
    st.session_state["approved_ids"].update(ids)
    df.loc[df["ID"].isin(ids), "Status"] = "Approved"

if col2.button("❌ Unapprove All Visible"):
    ids = filtered_df["ID"].dropna().tolist()
    st.session_state["approved_ids"].difference_update(ids)
    df.loc[df["ID"].isin(ids), "Status"] = ""

# --- Title ---
st.title("OT Summary – Visual Test")

# --- Display by Department ---
for dept in filtered_df["Department"].dropna().unique():
    dept_df = filtered_df[filtered_df["Department"] == dept]
    st.subheader(f"Department: {dept}")

    dept_df_display = dept_df.copy()

    # Format columns
    dept_df_display["Date"] = dept_df_display["Date"].dt.strftime("%m/%d")
    dept_df_display["Start"] = dept_df_display["Start"].apply(lambda x: x.strftime("%H:%M") if pd.notnull(x) else "")
    dept_df_display["End"] = dept_df_display["End"].apply(lambda x: x.strftime("%H:%M") if pd.notnull(x) else "")
    dept_df_display["Sum"] = dept_df_display["Sum"].apply(lambda x: f"{int(round(x)):,}" if pd.notnull(x) else "")

    # Mark approved rows
    dept_df_display["✔️ Approved"] = dept_df_display["ID"].apply(
        lambda id_: "✅" if id_ in st.session_state["approved_ids"] else ""
    )

    # Show table
    display_cols = ["✔️ Approved", "Date", "Name", "Title", "Start", "End", "OT", "Meal Penalty", "TA", "Sum"]
    st.dataframe(dept_df_display[display_cols])

    # Subtotals
    totals = dept_df[["OT", "Meal Penalty", "TA", "Sum"]].sum(numeric_only=True).round(0).astype(int)
    st.markdown(
        f"**Subtotal – OT:** `{totals['OT']:,}`  "
        f"**MP:** `{totals['Meal Penalty']:,}`  "
        f"**TA:** `{totals['TA']:,}`  "
        f"**Sum:** `{totals['Sum']:,}`"
    )

# --- Mark Status Before Export ---
filtered_df_export = filtered_df.copy()
filtered_df_export["Status"] = filtered_df_export["ID"].apply(
    lambda id_: "Approved" if id_ in st.session_state["approved_ids"] else ""
)

# --- Export Button ---
st.download_button(
    label="Download filtered data as CSV",
    data=filtered_df_export.to_csv(index=False),
    file_name="OT_summary_filtered.csv"
)

