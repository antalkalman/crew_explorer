import streamlit as st
import pandas as pd

# 👉 Enable wide mode
st.set_page_config(layout="wide")

# --- Load and Clean Data ---
df = pd.read_excel("/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/visual_test/data_for_visual_test.xlsx")

# Clean up column names (strip whitespace)
df.columns = df.columns.str.strip()

# Convert Date column to datetime
df["Date"] = pd.to_datetime(df["Date"])

st.sidebar.header("Filters")

# Unique options
unit_options = sorted(df["Unit"].dropna().unique())
dept_options = sorted(df["Department"].dropna().unique())
date_options = sorted(df["Date"].dt.date.unique())

# Unit filter with 'All'
unit_filter = st.sidebar.multiselect(
    "Select Unit(s)",
    options=["All"] + unit_options,
    default=["All"]
)
if "All" in unit_filter or not unit_filter:
    unit_filter = unit_options

# Department filter with 'All'
department_filter = st.sidebar.multiselect(
    "Select Department(s)",
    options=["All"] + dept_options,
    default=["All"]
)
if "All" in department_filter or not department_filter:
    department_filter = dept_options

# Date filter with 'All'
date_filter = st.sidebar.multiselect(
    "Select Date(s)",
    options=["All"] + date_options,
    default=["All"]
)
if "All" in date_filter or not date_filter:
    date_filter = date_options


# Apply filters
filtered_df = df[
    (df["Unit"].isin(unit_filter)) &
    (df["Department"].isin(department_filter)) &
    (df["Date"].dt.date.isin(date_filter))
]


# --- Title ---
st.title("OT Summary – Visual Test")

# --- Department Grouped Display ---
for dept in filtered_df["Department"].dropna().unique():
    dept_df = filtered_df[filtered_df["Department"] == dept]
    st.subheader(f"Department: {dept}")

    # Format for display
    dept_df_display = dept_df.copy()
    dept_df_display["Date"] = pd.to_datetime(dept_df_display["Date"], errors="coerce").dt.strftime("%m/%d")
    dept_df_display["Start"] = dept_df_display["Start"].apply(lambda x: x.strftime("%H:%M") if pd.notnull(x) else "")
    dept_df_display["End"] = dept_df_display["End"].apply(lambda x: x.strftime("%H:%M") if pd.notnull(x) else "")

    dept_df_display["Sum"] = dept_df_display["Sum"].apply(
        lambda x: f"{int(round(x)):,}" if pd.notnull(x) else ""
    )

    # Show table
    st.dataframe(dept_df_display[[
        "Date", "Name", "Title", "Start", "End", "OT", "Meal Penalty", "TA", "Sum"
    ]])

    # 🧮 Calculate subtotals BEFORE printing them
    totals = dept_df[["OT", "Meal Penalty", "TA", "Sum"]].sum(numeric_only=True).round(0).astype(int)

    # Show subtotals in one line
    st.markdown(
        f"**Subtotal – OT:** `{totals['OT']:,}`  "
        f"**MP:** `{totals['Meal Penalty']:,}`  "
        f"**TA:** `{totals['TA']:,}`  "
        f"**Sum:** `{totals['Sum']:,}`"
    )

# Optional export (for debugging or sharing)
st.download_button(
    label="Download filtered data as CSV",
    data=filtered_df.to_csv(index=False),
    file_name="OT_summary_filtered.csv"
)
