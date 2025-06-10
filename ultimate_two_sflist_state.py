import pandas as pd
import numpy as np
import re
from datetime import datetime
import os

# === Set SF_Archive directory ===
desktop_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/SF_Archive"
laptop_path = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/SF_Archive"
base_dir = desktop_path if os.path.exists(desktop_path) else laptop_path

temp_dir = os.path.join(base_dir, "Temp")
os.makedirs(temp_dir, exist_ok=True)

pattern = re.compile(r"SFlist_(\d{8}_\d{4})\.csv$")
sf_files = []

for f in os.listdir(base_dir):
    match = pattern.match(f)
    if match:
        try:
            ts = datetime.strptime(match.group(1), "%Y%m%d_%H%M")
            sf_files.append((ts, f))
        except ValueError:
            continue

if len(sf_files) < 2:
    raise FileNotFoundError("❌ Need at least two SFlist_YYYYMMDD_HHMM.csv files in the 'SF_Archive' folder.")

sf_files.sort(reverse=True)

# Process both latest and previous files
df_pm_views = []
for i in range(2):
    file_timestamp = sf_files[i][0].strftime("%Y%m%d_%H%M")
    file_path = os.path.join(base_dir, sf_files[i][1])

    excluded_projects = {"Death By Lightning", "Test", "Ballerina Overdrive", "Icebreaker"}

    df = pd.read_csv(file_path)
    df = df[~df["Project"].isin(excluded_projects)]
    df = df[df["State"] != "paused"]
    df = df[~df["Sf number"].astype(str).str.upper().str.startswith("CL")]

    columns_to_keep = [
        "ID", "Sf number", "Crew member id", "Project", "Currency", "User name", "User surname",
        "User email", "User phone", "Project department", "Project job title", "Project unit", "Title note", "State",
        "Surname", "Firstname", "Nickname", "Email", "Mobile number", "Crew list name", "Crew email", "Citizenship",
        "Start date", "End date", "Deal type",
        "Personal: Tax number / Adóazonosító jel", "Personal: Bank account number / Bankszámlaszám",
        "Company: VAT number / Adószám", "Company: Company name / Cégnév", "Company: Bank account number / Bankszámlaszám",
        "Daily fee", "Car allowance", "Phone allowance", "Computer allowance", "Offset meal",
        "Daily others 1 price", "Daily others 2 price",
        "Weekly fee", "Box rental", "Weekly others price", "Max computer allowance", "Fee others 1 price",
        "Project overtime", "Project turnaround", "Project working hour",
        "Bank account number"
    ]
    df = df[columns_to_keep].copy()

    def safe_str(x):
        return str(x).strip() if not pd.isna(x) else ""

    def clean_account(raw):
        digits = re.sub(r'\D', '', str(raw))
        return f"{digits[:8]}-{digits[8:16]}-{digits[16:24]}" if len(digits) >= 16 else digits

    def merge_tax_number(df):
        df["Personal: Tax number / Adóazonosító jel"] = df["Personal: Tax number / Adóazonosító jel"].fillna("").astype(str).str.strip()
        df["Company: VAT number / Adószám"] = df["Company: VAT number / Adószám"].fillna("").astype(str).str.strip()
        df["Tax Number"] = df["Personal: Tax number / Adóazonosító jel"]
        df["Tax Number"] = df["Tax Number"].where(df["Tax Number"] != "", df["Company: VAT number / Adószám"])
        df["Tax Number"] = df["Tax Number"].replace("", np.nan)
        return df

    def merge_bank_account(df):
        df["Bank Account"] = df["Personal: Bank account number / Bankszámlaszám"].apply(safe_str)
        df["Bank Account"] = df["Bank Account"].where(df["Bank Account"] != "", df["Company: Bank account number / Bankszámlaszám"].apply(safe_str))
        df["Bank Account"] = df["Bank Account"].where(df["Bank Account"] != "", df["Bank account number"].apply(safe_str))
        df["Bank Account"] = df["Bank Account"].apply(clean_account)
        return df

    def is_effectively_blank(s):
        if pd.isna(s):
            return True
        s = str(s).strip()
        return s == "" or s.lower() == "nan" or not re.search(r'[A-Za-z0-9]', s)

    def has_fee(row):
        return not (pd.isna(row.get("Daily fee")) and pd.isna(row.get("Weekly fee")))

    def find_issues(row, today):
        issues = []
        sf_type = str(row.get("Sf number", ""))[:2]

        if row.get("State") not in {"accepted", "signed"} and pd.notna(row.get("Start date")) and row["Start date"] < today:
            days_late = (today - row["Start date"]).days
            issues.append(f"Start date in past but not yet signed or accepted ({days_late} days)")

        if row.get("State") in {"accepted", "signed"}:
            required = [
                "Project department", "Project job title", "Project unit",
                "Surname", "Firstname", "Mobile number",
                "Crew list name", "Crew email", "Start date", "End date", "Deal type",
                "Project overtime", "Project turnaround", "Project working hour"
            ]

            if sf_type == "BD":
                required = [f for f in required if f not in {"Surname", "Firstname", "Mobile number", "Crew list name", "Crew email"}]

            for field in required:
                if is_effectively_blank(row.get(field, "")):
                    issues.append(field)

            if not has_fee(row):
                issues.append("Daily fee / Weekly fee")

            tax_number = row.get("Tax Number", "")
            company_name = row.get("Company: Company name / Cégnév", "")
            bank_account = row.get("Bank Account", "")

            if sf_type in {"BD", "DL"}:
                if is_effectively_blank(tax_number) and is_effectively_blank(company_name):
                    issues.append("Tax Number/Company")
            else:
                if is_effectively_blank(tax_number):
                    issues.append("Tax Number")
                if is_effectively_blank(bank_account):
                    issues.append("Bank Account")

        return ", ".join(issues)

    df["Start date"] = pd.to_datetime(df["Start date"], errors="coerce")
    today = pd.Timestamp(datetime.today().date())
    df = merge_tax_number(merge_bank_account(df))
    df["SF Key"] = df["Sf number"].astype(str) + " - " + df["Project"].astype(str)
    df["Issues"] = df.apply(lambda x: find_issues(x, today), axis=1)

    account_keywords = {"Tax Number", "Bank Account"}
    pm_keywords = {
        "Start date", "End date",
        "Daily fee", "Weekly fee",
        "Project overtime", "Project turnaround", "Project working hour",
        "Project unit", "Deal type"
    }

    def determine_responsible(issues):
        parts = [x.strip() for x in issues.split(",") if x.strip()]
        is_pm = any(any(k in part for k in pm_keywords) for part in parts)
        is_account = any(any(k in part for k in account_keywords) for part in parts)
        if is_pm and is_account:
            return "PM, Account"
        elif is_pm:
            return "PM"
        elif is_account:
            return "Account"
        return "Admin"

    def determine_priority(issues):
        parts = [x.strip() for x in issues.split(",") if x.strip()]
        if any(part in ["Start date", "End date", "Daily fee / Weekly fee", "Project overtime", "Project turnaround", "Project working hour"] for part in parts):
            return 1
        return 3

    df_issues = df[df["Issues"] != ""].copy()
    df_issues["Responsible"] = df_issues["Issues"].apply(determine_responsible)
    df_issues["Priority"] = df_issues["Issues"].apply(determine_priority)

    def determine_category(row):
        if "Start date in past but not yet signed or accepted" in row["Issues"]:
            state = row["State"].strip().lower()
            if state in {"sent", "in progress", "rejected"}:
                return "Chase"
            elif state == "draft":
                return "Plan?"
            elif state == "reviewing":
                return "Accept please"
        return row["Responsible"]

    df_issues["Category"] = df_issues.apply(determine_category, axis=1)

    category_to_who = {
        "Chase": "Admin",
        "Accept please": "PM",
        "Plan?": "PM",
        "PM": "PM",
        "PM, Account": "PM, Account",
        "Account": "Account",
        "Admin": "Admin"
    }
    df_issues["Who"] = df_issues["Category"].map(category_to_who)

    df_issues["ResponsibleOrder"] = df_issues["Responsible"].map({"PM": 1, "PM, Account": 2, "Account": 3})
    df_issues = df_issues.sort_values(by=["Project", "Priority", "ResponsibleOrder", "Sf number"])
    df_issues = df_issues.drop(columns=["ResponsibleOrder"])

    pm_columns = [
        "Project", "SF Key", "Sf number", "State", "Crew list name",
        "Project department", "Project job title", "Category", "Who", "Issues", "Priority"
    ]
    df_pm_view = df_issues[pm_columns].copy()

    category_order = {
        "Chase": 1,
        "Plan?": 2,
        "PM": 3,
        "PM, Account": 4,
        "Account": 5,
        "Accept please": 6
    }
    df_pm_view["CategorySort"] = df_pm_view["Category"].map(category_order)

    def extract_days(issue_text):
        match = re.search(r"\((\d+)\s+days\)", issue_text)
        return int(match.group(1)) if match else 0

    df_pm_view["DelayDays"] = df_pm_view["Issues"].apply(extract_days)

    df_pm_view = df_pm_view.sort_values(by=["Project", "CategorySort", "DelayDays"], ascending=[True, True, False])
    df_pm_view = df_pm_view.drop(columns=["CategorySort", "DelayDays"])

    df_pm_views.append((file_timestamp, df_pm_view))
    pm_view_path = os.path.join(temp_dir, f"SF_Issues_{file_timestamp}.csv")
    df_pm_view.to_csv(pm_view_path, index=False)
    print(f"✅ SF Issues exported: {pm_view_path}")


# === Export differences ===
latest_timestamp, latest_df = df_pm_views[0]
previous_timestamp, previous_df = df_pm_views[1]

key_cols = ["Project", "SF Key", "Sf number"]

latest_set = set(tuple(row) for row in latest_df[key_cols].values)
previous_set = set(tuple(row) for row in previous_df[key_cols].values)

new_only_rows = latest_set - previous_set
old_only_rows = previous_set - latest_set

df_new_only = latest_df[latest_df[key_cols].apply(tuple, axis=1).isin(new_only_rows)]
df_old_only = previous_df[previous_df[key_cols].apply(tuple, axis=1).isin(old_only_rows)]

new_path = os.path.join(temp_dir, f"New_Issues_{latest_timestamp}.csv")
old_path = os.path.join(temp_dir, f"Resolved_Issues_{previous_timestamp}.csv")

df_new_only.to_csv(new_path, index=False)
df_old_only.to_csv(old_path, index=False)

print(f"🟢 Difference export complete: {new_path}, {old_path}")
