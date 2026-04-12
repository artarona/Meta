import os
import sys

REQUIRED_ENV_VARS = [
    "ACCESS_TOKEN",
    "PHONE_NUMBER_ID",
    "VERIFY_TOKEN",
    "DATABASE_URL",
    "ADMIN_KEY"
]

REQUIRED_FILES = [
    "propiedades.json",
    "dias-horarios-visitas.json",
    "google_calendar_key.json"
]

def check_env():
    print("🔍 Checking environment variables...")
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing variables: {', '.join(missing)}")
        return False
    print("✅ All environment variables found.")
    return True

def check_files():
    print("🔍 Checking critical files...")
    missing = []
    for f in REQUIRED_FILES:
        if not os.path.exists(f):
            missing.append(f)
    
    if missing:
        print(f"❌ Missing files: {', '.join(missing)}")
        return False
    print("✅ All critical files found.")
    return True

if __name__ == "__main__":
    env_ok = check_env()
    files_ok = check_files()
    
    if not env_ok or not files_ok:
        print("\n⚠️ WARNING: System might not start correctly due to missing requirements.")
        # sys.exit(1) # Un-comment if you want to block startup
    else:
        print("\n🚀 System ready for takeoff!")
