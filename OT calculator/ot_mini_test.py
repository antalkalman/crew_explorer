import pandas as pd
from ot_utils import parse_time_input, get_ot_minutes, calculate_rounded_ot

# === Load input files ===
ot_types_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/DTS test/OT_types.xlsx"
dummy_dts_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/DTS test/Dummy_DTS.xlsx"

df_ot_types = pd.read_excel(ot_types_path)
df_dts = pd.read_excel(dummy_dts_path)

# === Rename for consistent keys ===
df_ot_types = df_ot_types.rename(columns={
    "OT name": "OT Deal",
    "Rounding period in minutes": "Rounding",
    "Grace in 1st hour": "Grace1",
    "Grace in other hours": "GraceOther"
})

# === Merge OT rules into dummy DTS ===
df = df_dts.merge(df_ot_types[["OT Deal", "Rounding", "Grace1", "GraceOther"]], on="OT Deal", how="left")

# === Calculate OT columns ===
def process_row(row):
    try:
        ot_min = get_ot_minutes(row["Start"], row["End"], row["F_WD"])
        ot_rounded = calculate_rounded_ot(
            ot_minutes=ot_min,
            period=row["Rounding"],
            grace_first=row["Grace1"],
            grace_other=row["GraceOther"]
        )
        return pd.Series([ot_min, ot_rounded])
    except Exception as e:
        print(f"❌ Error in row: {row.name} - {e}")
        return pd.Series([None, None])

df[["OT_minutes", "OT_rounded"]] = df.apply(process_row, axis=1)

# === Save output ===
output_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/DTS test/Dummy_DTS_with_OT.xlsx"
df.to_excel(output_path, index=False)
print(f"✅ File saved to: {output_path}")
