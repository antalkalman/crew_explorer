import os
import subprocess
import time

# === Define script paths for both computers ===
desktop_base = "/Users/kalmanantal"
laptop_base = "/Users/antalkalman"

# Determine which base path exists
if os.path.exists(desktop_base):
    base_user = "kalmanantal"
elif os.path.exists(laptop_base):
    base_user = "antalkalman"
else:
    raise FileNotFoundError("❌ Could not find valid user path.")

# Construct full paths
base_path = f"/Users/{base_user}/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/PyCharmprojects"
combined_script = os.path.join(base_path, "master_combined.py")
preprocess_script = os.path.join(base_path, "master_preprocess.py")

# === Run master_combined.py ===
print("🚀 Running master_combined.py ...")
subprocess.run(["python3", combined_script], check=True)
print("✅ master_combined.py finished")

# === Optional wait time if needed ===
# time.sleep(30)  # Uncomment and set delay in seconds if necessary

# === Run master_preprocess.py ===
print("🚀 Running master_preprocess.py ...")
subprocess.run(["python3", preprocess_script], check=True)
print("✅ master_preprocess.py finished")
