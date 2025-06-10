import os
import pandas as pd
import re
import unicodedata
import Levenshtein

def normalize_gcmid(x):
    try:
        return str(int(float(x)))
    except (ValueError, TypeError):
        return ""

# === Fixed input file to check ===
input_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database/input for consistency.xlsx"

# === Always use helpers from master combined file ===
helper_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database/Combined_All_CrewData.xlsx"

# === Output will be next to the input file ===
base_name = os.path.splitext(os.path.basename(input_path))[0]
output_path = os.path.join(os.path.dirname(input_path), f"{base_name}_Matched_GCMID.xlsx")

# === Load input file to check ===
df_input = pd.read_excel(input_path)

# === Validate input file columns ===
required_columns = ["Crew list name", "Mobile number", "Crew email"]
missing = [col for col in required_columns if col not in df_input.columns]

if missing:
    raise ValueError(f"❌ The input file is missing required columns: {', '.join(missing)}")
else:
    print("✅ Input file contains all required columns.")


# === Load helper sheets from Combined_All_CrewData.xlsx ===
df_tokens = pd.read_excel(helper_path, sheet_name="Tokenized Names")
df_tokens.rename(columns={"GCMID": "CM ID"}, inplace=True)

df_emails = pd.read_excel(helper_path, sheet_name="Emails")
df_emails.rename(columns={"GCMID": "CM ID"}, inplace=True)

df_phones = pd.read_excel(helper_path, sheet_name="Phones")
df_phones.rename(columns={"GCMID": "CM ID"}, inplace=True)

df_actual = pd.read_excel(helper_path, sheet_name="Actual Details")

# ✅ Load General Departments helper table (GCMID-based)
df_dept = pd.read_excel(helper_path, sheet_name="General Departments")
df_dept = df_dept[["GCMID", "General Department"]].copy()
df_dept.rename(columns={"GCMID": "CM ID", "General Department": "DB General Department"}, inplace=True)

df_dept.columns = [col.strip() for col in df_dept.columns]  # ✅ ADD THIS LINE
df_dept["CM ID"] = df_dept["CM ID"].apply(normalize_gcmid)


print("📄 df_dept sample:\n", df_dept.head())


# === Normalize helpers ===
nickname_map = {
    "gabi": "gabriella", "zsuzsa": "zsuzsanna", "zsuzsi": "zsuzsanna", "gergo": "gergely",
    "kati": "katalin", "erzsi": "erzsebet", "bobe": "erzsebet", "bori": "borbala",
    "dani": "daniel", "moni": "monika", "zoli": "zoltan", "niki": "nikoletta",
    "pisti": "istvan", "magdi": "magdolna", "jr": "junior", "jrxx": "junior",
    "orsi": "orsolya", "ricsi": "richard", "gyuri": "gyorgy"
}

def strip_accents(text):
    return ''.join(c for c in unicodedata.normalize('NFD', str(text)) if unicodedata.category(c) != 'Mn')

def normalize_phone(phone):
    phone = str(phone)
    phone = re.sub(r'\D', '', phone)
    if phone.startswith("36"):
        phone = phone[2:]
    elif phone.startswith("06"):
        phone = phone[2:]
    elif phone.startswith("6"):
        phone = phone[1:]
    return "36" + phone if phone else ""


def clean_text(text):
    text = strip_accents(str(text)).lower().strip()
    return re.sub(r"[\"'’().\s]", "", text)

def tokenize_name(name):
    if not isinstance(name, str):
        return []
    name = strip_accents(name.lower())
    name = re.sub(r"[\"'’().]", "", name)
    tokens = re.findall(r'\b\w+\b', name)
    return [nickname_map.get(tok, tok) for tok in tokens if tok != "né"]

def token_match_score(input_token, target_token):
    if input_token == target_token:
        return 1.0
    if target_token.startswith(input_token) and len(input_token) >= 2:
        return 0.75
    dist = Levenshtein.distance(input_token, target_token)
    return 0.5 if dist == 1 else 0.25 if dist == 2 else 0.0

def fuzzy_name_score(input_name):
    input_tokens = tokenize_name(input_name)
    grouped = df_tokens.groupby("CM ID")["Token"].apply(list).reset_index()

    def score_row(tokens):
        return sum(max((token_match_score(t, tok) for tok in tokens), default=0) for t in input_tokens)

    grouped["NameScore"] = grouped["Token"].apply(score_row)
    return grouped[["CM ID", "NameScore"]]

def apply_department_score(df_merge, general_dept):
    # Ensure consistent formatting
    df_merge["CM ID"] = df_merge["CM ID"].apply(normalize_gcmid)
    df_dept["CM ID"] = df_dept["CM ID"].apply(normalize_gcmid)

    if general_dept is not None and general_dept.strip() != "":
        df_merge = df_merge.merge(df_dept, on="CM ID", how="left")

        print("📊 Columns after merge:", df_merge.columns.tolist())
        print("🔍 Non-null DB General Department values:", df_merge["DB General Department"].notna().sum())

        df_merge["DeptScore"] = df_merge["DB General Department"].apply(
            lambda x: 0.5 if pd.notna(x) and x == general_dept else 0.0
        )
    else:
        df_merge["DeptScore"] = 0.0

    return df_merge




def find_best_matches(name, email, phone, general_dept=None):  # ⬅ add general_dept param
    phone_input = normalize_phone(phone)
    email_input = clean_text(email)

    df_name_scores = fuzzy_name_score(name)

    df_emails["CleanEmail"] = df_emails["Email"].fillna("").apply(clean_text)
    df_emails["EmailScore"] = df_emails["CleanEmail"].apply(
        lambda x: 1.0 if x == email_input else 0.5 if Levenshtein.distance(x, email_input) == 1 else 0.0
    )

    df_phones["FormattedPhone"] = df_phones["Phone"].apply(normalize_phone)
    df_phones["PhoneScore"] = df_phones["FormattedPhone"].apply(
        lambda x: 1.0 if x == phone_input else 0.5 if Levenshtein.distance(x, phone_input) == 1 else 0.0
    )

    df_merge = df_name_scores.merge(df_emails[["CM ID", "EmailScore"]], on="CM ID", how="outer")
    df_merge = df_merge.merge(df_phones[["CM ID", "PhoneScore"]], on="CM ID", how="outer")
    df_merge.fillna(0, inplace=True)

    print("🆔 df_merge CM ID sample:\n", df_merge["CM ID"].astype(str).drop_duplicates().head())

    df_merge = apply_department_score(df_merge, general_dept)
    if "DB General Department" in df_merge.columns:
        print("✅ DeptScore rows > 0:\n",
              df_merge[df_merge["DeptScore"] > 0][["CM ID", "DB General Department", "DeptScore"]])
    else:
        print("✅ DeptScore rows > 0:\n",
              df_merge[df_merge["DeptScore"] > 0][["CM ID", "DeptScore"]])

    if "DB General Department" in df_merge.columns:
        print("🔍 DeptScore debug:\n",
              df_merge[["CM ID", "DeptScore", "DB General Department"]].query("DeptScore > 0"))
    else:
        print("🔍 DeptScore debug:\n",
              df_merge[["CM ID", "DeptScore"]].query("DeptScore > 0"))

    df_merge["FinalScore"] = (
        df_merge["NameScore"] * 1.5
        + df_merge["EmailScore"]
        + df_merge["PhoneScore"]
        + df_merge["DeptScore"]  # ✅ include in score
    )
    df_merge = df_merge[df_merge["FinalScore"] > 0]
    df_merge = df_merge.sort_values(by=["FinalScore", "NameScore", "CM ID"], ascending=[False, False, True])
    return df_merge




# === Use ALL rows with valid names — even those with GCMID (for consistency check)
df_check = df_input[df_input["Crew list name"].notna()].copy()

# Rename email for matching
if "Crew email" in df_check.columns:
    df_check.rename(columns={"Crew email": "Email"}, inplace=True)

# Prepare phone alias
df_check["Phone"] = df_check["Mobile number"]


confirmed_rows = []
maybe_rows = []


total = len(df_check)

for i, (idx, row) in enumerate(df_check.iterrows(), 1):
    if i % 100 == 0 or i == total:
        print(f"🔄 Processed {i}/{total} rows...")

    # your matching logic here

    matches = find_best_matches(
        row["Crew list name"],
        row.get("Email", ""),
        row.get("Phone", ""),
        row.get("General Department", "")  # 👈 Add this line
    )

    if not matches.empty and matches.iloc[0]["NameScore"] >= 1.25 and (matches.iloc[0]["EmailScore"] + matches.iloc[0]["PhoneScore"]) >= 1.0:
        best = matches.iloc[0]
        combined = row.to_dict()

        # Try to include the useful fields from the input data if available
        combined.update({
            "Surname": row.get("Surname", ""),
            "Firstname": row.get("Firstname", ""),
            "Nickname": row.get("Nickname", ""),
            "General Title": row.get("General Title", ""),
            "Mobile number": row.get("Mobile number", ""),
            "Email": row.get("Email", "")
        })

        # Add extra identity fields if available in original df_input
        for field in ["Surname", "Firstname", "Nickname", "General Title", "Mobile number", "Email"]:
            combined[field] = df_input.loc[row.name, field] if field in df_input.columns else ""


        existing = normalize_gcmid(row.get("GCMID", ""))
        matched = normalize_gcmid(best["CM ID"])

        combined.update({
            "NameScore": best["NameScore"],
            "EmailScore": best["EmailScore"],
            "PhoneScore": best["PhoneScore"],
            "DeptScore": best.get("DeptScore", 0),  # <-- add this line
            "FinalScore": best["FinalScore"],
            "Existing GCMID": existing,
            "Matched CM ID": matched,
            "Match Status": "✅ Match" if existing == matched else "❌ MISMATCH",
        })

        confirmed_rows.append(combined)

    else:
        # Filter out low score options
        matches = matches[matches["FinalScore"] >= 1.25]

        # Drop duplicate GCMIDs, keeping only the best per person
        matches = matches.drop_duplicates(subset="CM ID", keep="first")

        # Limit to top 3 different GCMIDs
        top_matches = matches.head(3)

        for _, match in top_matches.iterrows():
            combined = row.to_dict()
            existing = normalize_gcmid(row.get("GCMID", ""))
            matched = normalize_gcmid(match["CM ID"])

            combined.update({
                "Suggested CM ID": matched,
                "Existing GCMID": existing,
                "Match Status": "✅ Match" if existing == matched else "❌ MISMATCH",
                "NameScore": match["NameScore"],
                "EmailScore": match["EmailScore"],
                "PhoneScore": match["PhoneScore"],
                "DeptScore": match.get("DeptScore", 0),
                "FinalScore": match["FinalScore"]
            })

            maybe_rows.append(combined)

# === Load trusted name info with clear, unique column names ===
names_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database/Names.xlsx"
df_names_info = pd.read_excel(names_path, sheet_name="Names", engine="openpyxl")[
    ["CM ID", "Sure Name", "First Name", "Actual Title"]
]

# Rename for clarity to avoid merging conflicts
df_names_info.rename(columns={
    "CM ID": "GCMID",
    "Sure Name": "DB Surname",
    "First Name": "DB Firstname",
    "Actual Title": "DB Title"
}, inplace=True)

# Create clean full name
df_names_info["Matched Name"] = df_names_info["DB Surname"].astype(str).str.strip() + " " + df_names_info["DB Firstname"].astype(str).str.strip()

# Final trusted fields to use
df_names_info = df_names_info[["GCMID", "Matched Name", "DB Surname", "DB Firstname", "DB Title"]]


# === Merge into output DataFrames with clean layout ===
maybe_rows_raw = maybe_rows.copy()
for df in [confirmed_rows, maybe_rows]:
    if df:
        df_temp = pd.DataFrame(df)



        # Create unique project key
        df_temp["CM ID--Project"] = df_temp["Crew member id"].astype(str) + "--" + df_temp["Project"].astype(str)

        df_temp["GCMID"] = df_temp["GCMID"].fillna("").astype(str)
        df_names_info["GCMID"] = df_names_info["GCMID"].astype(str)


        def normalize_gcmid(x):
            try:
                return str(int(float(x)))
            except (ValueError, TypeError):
                return ""


        # Rename first — this creates the 'Suggested CM ID' column
        df_temp.rename(columns={
            "Matched CM ID": "Suggested CM ID",
            "Crew list name": "Name on crew list"
        }, inplace=True)

        # Then normalize the Suggested CM ID (after the rename)
        df_temp["Suggested CM ID"] = df_temp["Suggested CM ID"].apply(normalize_gcmid)
        df_names_info["GCMID"] = df_names_info["GCMID"].apply(normalize_gcmid)

        # Now it's safe to merge
        df_temp = df_temp.merge(df_names_info, left_on="Suggested CM ID", right_on="GCMID", how="left")
        #df_temp.drop(columns=["GCMID"], inplace=True)

        print("Columns available in df_temp:", df_temp.columns.tolist())

        # Reorder and keep only final display columns
        df_temp = df_temp[[
            "CM ID--Project",
            "Existing GCMID",
            "Suggested CM ID",  # ✅ this replaces "Matched CM ID"
            "Match Status",
            "Name on crew list",
            "Project job title",
            "Matched Name",
            "DB Surname",
            "DB Firstname",
            "DB Title",
            "NameScore",
            "EmailScore",
            "PhoneScore",
            "DeptScore",  # ✅ Correct name and fixed missing comma
            "FinalScore",
        ]]

        # Replace original list
        df.clear()
        df.extend(df_temp.to_dict(orient="records"))



# === Export All Results ===
with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    df_confirmed = pd.DataFrame(confirmed_rows)
    df_maybe = pd.DataFrame(maybe_rows)
    new_names_df = pd.DataFrame(maybe_rows_raw)

    if not df_confirmed.empty:
        df_confirmed["PhoneScore"] = df_confirmed["PhoneScore"].astype(str)
        df_confirmed["Name on crew list"] = df_confirmed["Name on crew list"].astype(str)
        df_confirmed.to_excel(writer, sheet_name="Confirmed Matches", index=False)

    if not df_maybe.empty:
        df_maybe.to_excel(writer, sheet_name="Possible Matches", index=False)

    # Clean and format "Possible New Names"
    if "Mobile number" in new_names_df.columns:
        new_names_df["Mobile number"] = new_names_df["Mobile number"].astype(str)

    fields = ["Surname", "Firstname", "Nickname", "General Title", "Mobile number", "Email"]
    available_fields = [col for col in fields if col in new_names_df.columns]
    new_names_df = new_names_df[available_fields].copy().drop_duplicates()

    new_names_df.to_excel(writer, sheet_name="Possible New Names", index=False)

print("✅ Matching completed and saved to:", output_path)
print(f"🧮 Total maybe_rows_raw: {len(new_names_df)}")
print("🧾 Available columns in maybe_rows_raw:", new_names_df.columns.tolist())








