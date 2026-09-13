import os
import sys

def find_null_bytes_in_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            if b'\x00' in content:
                print(f"❌ Null byte found in: {filepath}")
                return True
        return False
    except Exception as e:
        print(f"⚠️ Could not read {filepath}: {e}")
        return False

def find_null_bytes_in_directory(directory):
    found = False
    for root, dirs, files in os.walk(directory):
        # Skip virtual environment and cache directories
        if 'venv' in root or '__pycache__' in root or 'migrations' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if find_null_bytes_in_file(filepath):
                    found = True
    return found

if __name__ == "__main__":
    print("🔍 Searching for null bytes in Python files...")
    if find_null_bytes_in_directory('.'):
        print("\n❌ Found files with null bytes. Please check the files above.")
        sys.exit(1)
    else:
        print("✅ No null bytes found!")
        sys.exit(0)