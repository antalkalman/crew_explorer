import pandas as pd
import re
import unicodedata
import Levenshtein

# === Paths ===
input_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/Master_database/Combined_crew_source_test.xlsx"
output_path = input_path.replace("Combined_crew_source_test.xlsx", "Matched_GCMID_from_helpers.xlsx")

# === Load data ===
df_input = pd.read_excel(input_path)
df_tokens = pd.read_excel(input_path, sheet_name="Tokenized Names")
df_emails = pd.read_excel(input_path, sheet_name="Emails")
df_phones = pd.read_excel(input_path, sheet_name="Phones")
df_actual = pd.read_excel(input_path, sheet_name="Actual Details")


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

def find_best_matches(name, email, phone):
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

    df_merge["FinalScore"] = df_merge["NameScore"] * 1.5 + df_merge["EmailScore"] + df_merge["PhoneScore"]
    df_merge = df_merge[df_merge["FinalScore"] > 0]
    df_merge = df_merge.sort_values(by=["FinalScore", "NameScore", "CM ID"], ascending=[False, False, True])
    return df_merge

# === Filter for matching ===
# === Filter for matching ===
# More robust check: detect NaN, empty string, and whitespace-only GCMIDs
df_missing = df_input[
    df_input["Crew list name"].notna() &
    (
        df_input["GCMID"].isna() |
        (df_input["GCMID"].astype(str).str.strip() == "")
    )
].copy()

df_missing = df_missing[df_missing["Crew list name"].notna()]



confirmed_rows = []
maybe_rows = []

for _, row in df_missing.iterrows():
    matches = find_best_matches(row["Crew list name"], row.get("Email", ""), row.get("Mobile number", ""))

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

        combined.update({
            "Matched CM ID": match["CM ID"],
            "GCMID": match["CM ID"],
            "NameScore": match["NameScore"],
            "EmailScore": match["EmailScore"],
            "PhoneScore": match["PhoneScore"],
            "FinalScore": match["FinalScore"],
        })
        maybe_rows.append(combined)

    else:
        top3 = matches.head(3)
        if top3.empty:
            print(f"🔍 No matches for: {row['Crew list name']}")
        else:
            print(f"👀 Possible matches for {row['Crew list name']}:")
            print(top3[["CM ID", "NameScore", "EmailScore", "PhoneScore", "FinalScore"]])

        for _, match in top3.iterrows():
            combined = row.to_dict()
            combined.update({
                "Matched CM ID": match["CM ID"],
                "GCMID": match["CM ID"],
                "NameScore": match["NameScore"],
                "EmailScore": match["EmailScore"],
                "PhoneScore": match["PhoneScore"],
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
        df_temp["CM ID--Project"] = df_temp["CM ID"].astype(str) + "--" + df_temp["Project"].astype(str)

        df_temp["GCMID"] = df_temp["GCMID"].fillna("").astype(str)
        df_names_info["GCMID"] = df_names_info["GCMID"].astype(str)

        # Normalize GCMID values in both dataframes to strings without decimals
        df_temp["GCMID"] = df_temp["GCMID"].apply(lambda x: str(int(float(x))) if pd.notna(x) else "")
        df_names_info["GCMID"] = df_names_info["GCMID"].astype(str)

        # Merge in trusted name fields without collisions
        df_temp = df_temp.merge(df_names_info, on="GCMID", how="left")

        # Rename for clarity
        df_temp.rename(columns={
            "Matched CM ID": "Suggested CM ID",
            "Crew list name": "Name on crew list"
        }, inplace=True)

        print("Columns available in df_temp:", df_temp.columns.tolist())

        # Reorder and keep only final display columns
        df_temp = df_temp[[
            "CM ID--Project",
            "Suggested CM ID",
            "Name on crew list",
            "Project job title",
            "Matched Name",
            "DB Surname",
            "DB Firstname",
            "DB Title",
            "NameScore",
            "EmailScore",
            "PhoneScore",
            "FinalScore",
        ]]

        # Replace original list
        df.clear()
        df.extend(df_temp.to_dict(orient="records"))




# === Export ===
with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
    pd.DataFrame(confirmed_rows).to_excel(writer, sheet_name="Confirmed Matches", index=False)
    pd.DataFrame(maybe_rows).to_excel(writer, sheet_name="Possible Matches", index=False)

print("✅ Matching completed and saved to:", output_path)

# === Extract simplified possible new names ===
fields = ["Surname", "Firstname", "Nickname", "General Title", "Mobile number", "Email"]

new_names_df = pd.DataFrame(maybe_rows_raw)  # ✅ use the raw copy with original fields

print(f"🧮 Total maybe_rows_raw: {len(new_names_df)}")
print("🧾 Available columns in maybe_rows_raw:", new_names_df.columns.tolist())

available_fields = [col for col in fields if col in new_names_df.columns]
new_names_df = new_names_df[available_fields].copy()
new_names_df.drop_duplicates(inplace=True)

with pd.ExcelWriter(output_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
    new_names_df.to_excel(writer, sheet_name="Possible New Names", index=False)

print("🆕 'Possible New Names' sheet added to:", output_path)







