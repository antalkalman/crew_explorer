import subprocess
import time
import os
import sys

# === Detect base user path (desktop vs laptop) ===
desktop_path = "/Users/kalmanantal/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/PyCharmprojects"
laptop_path = "/Users/antalkalman/Dropbox (Personal)/WORK/Pioneer Pictures/Adatbázis/PyCharmprojects"

base_dir = desktop_path if os.path.exists(desktop_path) else laptop_path

# === Full paths to scripts ===
full_export_script = os.path.join(base_dir, "full_export_api_SFlist.py")
check_script = os.path.join(base_dir, "sf_state_simple_SFlist.py")

if not os.path.exists(full_export_script) or not os.path.exists(check_script):
    print("❌ Could not find one or both scripts. Check paths.")
    sys.exit(1)

# === Run Step 1: Export Start Forms ===
print("🚀 Step 1: Exporting Start Forms from Crew Manager API...")
start_time = time.time()
export_result = subprocess.run(["python3", full_export_script])

if export_result.returncode != 0:
    print("❌ Export failed.")
    sys.exit(1)

elapsed = time.time() - start_time
print(f"✅ Export finished in {elapsed:.1f} seconds.\n")

# === Run Step 2: Check Start Forms ===
print("🔍 Step 2: Checking Start Forms for issues...")
check_result = subprocess.run(["python3", check_script])

if check_result.returncode != 0:
    print("❌ Issue checking failed.")
    sys.exit(1)

print("✅ All steps completed successfully.")
