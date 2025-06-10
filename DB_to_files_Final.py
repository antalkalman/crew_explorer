import pandas as pd
import re
import unicodedata

# === File paths ===
master_path = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/PY/Crew Master.xlsx"
output_path = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/PY/Preprocessed_Master.xlsx"

# === Load master and phonebook sheets ===
df_master = pd.read_excel(master_path, sheet_name="Full Crew Data")
df_master.columns = df_master.columns.str.strip()

df_phonebook = pd.read_excel(master_path, sheet_name="Names")
df_phonebook.columns = df_phonebook.columns.str.strip()

# === Nickname dictionary ===
nickname_map = {
    "gabi": "gabriella", "zsuzsa": "zsuzsanna", "zsuzsi": "zsuzsanna", "gergo": "gergely",
    "kati": "katalin", "erzsi": "erzsebet", "bobe": "erzsebet", "bori": "borbala",
    "dani": "daniel", "moni": "monika", "zoli": "zoltan", "niki": "nikoletta",
    "pisti": "istvan", "magdi": "magdolna", "jr": "junior", "jrxx": "junior",
    "orsi": "orsolya", "ricsi": "richard", "gyuri": "gyorgy"
}


# === Helper functions ===
def phone_format2(s):
    if isinstance(s, float) and s.is_integer():
        s = str(int(s))
    else:
        s = str(s)
    s = re.sub(r'\D', '', s)
    if s.startswith("36"):
        s = s[2:]
    elif s.startswith("06"):
        s = s[2:]
    elif s.startswith("6"):
        s = s[1:]
    return "36" + s if s else ""

def clean_company_number(s):
    return re.sub(r'\D', '', str(s))

def strip_accents(text):
    if not isinstance(text, str):
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')


def clean_name_text(text):
    text = strip_accents(text)
    text = re.sub(r"[\"'’\.]", "", text)
    return text.strip()

def cmid_comb_name_list(name, cmid):
    name = clean_name_text(name)
    parts = [p for p in name.split() if len(p) >= 3]
    variations = set()
    for i in range(len(parts)):
        for j in range(i + 2, len(parts) + 1):
            combo = " ".join(parts[i:j])
            variations.add(combo)
    full_name = " ".join(parts)
    if full_name:
        variations.add(full_name)
    if len(parts) > 1:
        flipped = " ".join(reversed(parts))
        variations.add(flipped)
        for i in range(len(parts)):
            for j in range(i + 2, len(parts) + 1):
                combo = " ".join(reversed(parts[i:j]))
                variations.add(combo)
    df = pd.DataFrame(list(variations), columns=["Name"])
    df["CM ID"] = cmid
    return df

# === Step 1: Merge & clean raw data ===
df_master_part = df_master[["GCM ID", "Crew list name", "Mobile number", "Crew email", "Company number"]].copy()
df_master_part.columns = ["CM ID", "Name", "Phone", "Email", "Company"]

df_phonebook_part = df_phonebook[["CM ID", "Name", "Actual Phone", "Actual Email"]].copy()
df_phonebook_part.columns = ["CM ID", "Name", "Phone", "Email"]
df_phonebook_part["Company"] = ""

df_combined = pd.concat([df_master_part, df_phonebook_part], ignore_index=True)
df_combined.dropna(subset=["CM ID"], inplace=True)
def is_clean_id(x):
    try:
        return float(x).is_integer()
    except:
        return False

df_combined = df_combined[df_combined["CM ID"].apply(is_clean_id)]
df_combined["CM ID"] = df_combined["CM ID"].astype(int)

df_combined["CM ID"] = df_combined["CM ID"].astype(int)
df_combined["Phone"] = df_combined["Phone"].apply(phone_format2)
df_combined["Company"] = df_combined["Company"].apply(clean_company_number)

# === Step 2: Actual Details ===
df_actual = df_combined.copy()
df_actual.columns = ["CM ID", "Actual Name", "Actual Phone", "Actual Email", "Company"]
df_actual = df_actual.sort_values(by="CM ID")

# === Step 3: Names (with combinations) ===
df_names = pd.DataFrame(columns=["CM ID", "Name"])
for _, row in df_actual.iterrows():
    name_variants = cmid_comb_name_list(row["Actual Name"], row["CM ID"])
    df_names = pd.concat([df_names, name_variants], ignore_index=True)
df_names["CM ID"] = df_names["CM ID"].astype(int)
df_names = df_names.drop_duplicates().sort_values(by="CM ID")

# === Step 4: Phones ===
df_phones = df_actual[["CM ID", "Actual Phone"]].copy()
df_phones.columns = ["CM ID", "Phone"]
df_phones["Phone"] = df_phones["Phone"].astype(str).str.strip()
df_phones = df_phones[df_phones["Phone"] != ""]
df_phones = df_phones.drop_duplicates().sort_values(by="CM ID")

# === Step 5: Emails ===
df_emails = df_actual[["CM ID", "Actual Email"]].copy()
df_emails.columns = ["CM ID", "Email"]
df_emails["Email"] = df_emails["Email"].astype(str).str.strip()
df_emails["Email"] = df_emails["Email"].replace(r"^\s*(nan|NaN|None)?\s*$", "", regex=True)
df_emails = df_emails[df_emails["Email"].str.contains("@")]
df_emails = df_emails.drop_duplicates().sort_values(by="CM ID")

# === Step 6: Companies ===
df_companies = df_actual[["CM ID", "Company"]].copy()
df_companies["Company"] = df_companies["Company"].astype(str).str.strip()
df_companies = df_companies[df_companies["Company"] != ""]
df_companies = df_companies.drop_duplicates().sort_values(by="CM ID")

# === Step 7: Tokenized Names ===
def clean_token(text):
    text = strip_accents(text.lower())
    text = re.sub(r"[\"'’().]", "", text)
    return text.strip()

def tokenize_name(name):
    if not isinstance(name, str):
        return []
    tokens = clean_token(name).split()
    return [nickname_map.get(tok, tok) for tok in tokens if len(tok) >= 3 and tok != "né"]

# Pull from df_actual — already clean
df_names_all = df_actual[["CM ID", "Actual Name"]].copy()
df_names_all.columns = ["CM ID", "Name"]
df_names_all.dropna(subset=["CM ID", "Name"], inplace=True)
df_names_all["CM ID"] = df_names_all["CM ID"].astype(int)

# Generate tokens
df_tokens = pd.DataFrame(columns=["CM ID", "Token"])
for _, row in df_names_all.iterrows():
    tokens = tokenize_name(row["Name"])
    for token in tokens:
        df_tokens = pd.concat([
            df_tokens,
            pd.DataFrame([{"CM ID": row["CM ID"], "Token": token}])
        ], ignore_index=True)

df_tokens = df_tokens.drop_duplicates().sort_values(by=["CM ID", "Token"])


# === Save to file ===
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df_actual.to_excel(writer, sheet_name='Actual Details', index=False)
    df_names.to_excel(writer, sheet_name='Names', index=False)
    df_phones.to_excel(writer, sheet_name='Phones', index=False)
    df_emails.to_excel(writer, sheet_name='Emails', index=False)
    df_companies.to_excel(writer, sheet_name='Companies', index=False)
    df_tokens.to_excel(writer, sheet_name='Tokenized Names', index=False)

print("✅ Preprocessing completed and saved to 'Preprocessed_Master.xlsx' with Tokenized Names.")
