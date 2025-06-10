import streamlit as st
import pandas as pd

# 👉 Enable wide mode
st.set_page_config(layout="wide")

# --- Load and Clean Data ---
df = pd.read_excel("/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/visual_test/data_for_visual_test.xlsx")
df.columns = df.columns.str.strip()
df["Date"] = pd.to_datetime(df["Date"])

# --- Sidebar Filters ---
st.sidebar.header("Filters")

unit_options = sorted(df["Unit"].dropna().unique())
dept_options = sorted(df["Department"].dropna().unique())
date_options = sorted(df["Date"].dt.date.unique())

unit_filter = st.sidebar.multiselect("Select Unit(s)", ["All"] + unit_options, default=["All"])
if "All" in unit_filter or not unit_filter:
    unit_filter = unit_options

department_filter = st.sidebar.multiselect("Select Department(s)", ["All"] + dept_options, default=["All"])
if "All" in department_filter or not department_filter:
    department_filter = dept_options

date_filter = st.sidebar.multiselect("Select Date(s)", ["All"] + date_options, default=["All"])
if "All" in date_filter or not date_filter:
    date_filter = date_options

# --- Apply Filters ---
filtered_df = df[
    (df["Unit"].isin(unit_filter)) &
    (df["Department"].isin(department_filter)) &
    (df["Date"].dt.date.isin(date_filter))
]

# --- Approval State ---
if "approved_ids" not in st.session_state:
    st.session_state["approved_ids"] = set()

# --- Approve All Visible Button ---
if st.button("✅ Approve All Visible Entries"):
    ids_to_approve = filtered_df["Record"].dropna().tolist()
    st.session_state["approved_ids"].update(ids_to_approve)
    df.loc[df["Record"].isin(ids_to_approve), "Status"] = "Approved"

# --- Title ---
st.title("OT Summary – Visual Test")

# --- Department Grouped View ---
for dept in filtered_df["Department"].dropna().unique():
    dept_df = filtered_df[filtered_df["Department"] == dept]
    st.subheader(f"Department: {dept}")

    dept_df_display = dept_df.copy()

    # Format columns
    dept_df_display["Date"] = dept_df_display["Date"].dt.strftime("%m/%d")
    dept_df_display["Start"] = dept_df_display["Start"].apply(lambda x: x.strftime("%H:%M") if pd.notnull(x) else "")
    dept_df_display["End"] = dept_df_display["End"].apply(lambda x: x.strftime("%H:%M") if pd.notnull(x) else "")
    dept_df_display["Sum"] = dept_df_display["Sum"].apply(lambda x: f"{int(round(x)):,}" if pd.notnull(x) else "")

    # Track approval/unapproval
    approved_ids = st.session_state["approved_ids"]
    unapproved_ids = set()
    approval_flags = []

    for _, row in dept_df_display.iterrows():
        rid = row["Record"]
        if rid in approved_ids:
            # Show checkbox to unapprove
            unapprove = st.checkbox(f"❌ Unapprove {row['Name']} on {row['Date']}", key=f"unapprove_{rid}")
            if unapprove:
                unapproved_ids.add(rid)
                approval_flags.append("")
            else:
                approval_flags.append("✅")
        else:
            approval_flags.append("")

    # Update display + state
    dept_df_display["✔️ Approved"] = approval_flags
    approved_ids.difference_update(unapproved_ids)
    df.loc[df["Record"].isin(unapproved_ids), "Status"] = ""

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

# --- Export Button ---
st.download_button(
    label="Download filtered data as CSV",
    data=filtered_df.to_csv(index=False),
    file_name="OT_summary_filtered.csv"
)
