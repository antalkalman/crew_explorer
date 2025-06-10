import subprocess
import time
import os
import sys

# === Detect base user path (desktop vs laptop) ===
desktop_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/PyCharmprojects"
laptop_path = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/PyCharmprojects"

base_dir = desktop_path if os.path.exists(desktop_path) else laptop_path

# === Full paths to scripts ===
full_export_script = os.path.join(base_dir, "Ultimate_full_export_api.py")
check_script = os.path.join(base_dir, "ultimate_daily_check.py")

if not os.path.exists(full_export_script) or not os.path.exists(check_script):
    print("❌ Could not find one or both scripts. Check paths.")
    sys.exit(1)

# === Run Step 1: Export Start Forms ===
print("🚀 Step 1: Exporting latest SFlist...")
start_time = time.time()
export_result = subprocess.run(["python3", full_export_script])

if export_result.returncode != 0:
    print("❌ Export failed.")
    sys.exit(1)

elapsed = time.time() - start_time
print(f"✅ Export completed in {elapsed:.1f} seconds.\n")

# === Wait buffer to ensure file is written ===
print("⏳ Waiting 10 seconds to ensure files are saved...")
time.sleep(10)

# === Run Step 2: Perform full daily check ===
print("📊 Step 2: Running daily SF check...")
check_result = subprocess.run(["python3", check_script])

if check_result.returncode != 0:
    print("❌ Daily check failed.")
    sys.exit(1)

print("🎉 All steps completed successfully.")
