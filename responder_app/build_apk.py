import os
import subprocess
import sys

def run_cmd(cmd, cwd=None):
    print(f"Running: {cmd} in {cwd or '.'}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error: Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

def main():
    responder_dir = os.path.abspath(os.path.dirname(__file__))
    
    # 1. Initialize Flutter project if not already initialized
    android_dir = os.path.join(responder_dir, 'android')
    if not os.path.exists(android_dir):
        print("Initializing Flutter project...")
        run_cmd("flutter create --offline --platforms=android .", cwd=responder_dir)
    else:
        print("Flutter project already initialized.")
        
    # 2. Add http dependency if not present in pubspec.yaml
    pubspec_path = os.path.join(responder_dir, 'pubspec.yaml')
    if os.path.exists(pubspec_path):
        with open(pubspec_path, 'r') as f:
            content = f.read()
        if 'http:' not in content:
            print("Adding http package dependency...")
            run_cmd("flutter pub add http", cwd=responder_dir)
    else:
        print("Error: pubspec.yaml not found after initialization.")
        sys.exit(1)
        
    # 3. Enable cleartext traffic in AndroidManifest.xml
    manifest_path = os.path.join(responder_dir, 'android', 'app', 'src', 'main', 'AndroidManifest.xml')
    if os.path.exists(manifest_path):
        print("Configuring AndroidManifest.xml for cleartext traffic...")
        with open(manifest_path, 'r') as f:
            manifest_content = f.read()
            
        # Add usesCleartextTraffic="true" to <application>
        if 'android:usesCleartextTraffic="true"' not in manifest_content:
            target = '<application'
            if target in manifest_content:
                manifest_content = manifest_content.replace(
                    target,
                    '<application\n        android:usesCleartextTraffic="true"'
                )
                with open(manifest_path, 'w') as f:
                    f.write(manifest_content)
                print("AndroidManifest.xml updated successfully.")
            else:
                print("Warning: <application> tag not found in AndroidManifest.xml")
    else:
        print("Warning: AndroidManifest.xml not found.")
        
    # 4. Build APK
    print("Building APK...")
    run_cmd("flutter build apk --release", cwd=responder_dir)
    
    apk_path = os.path.join(responder_dir, 'build', 'app', 'outputs', 'flutter-apk', 'app-release.apk')
    if os.path.exists(apk_path):
        print("\n" + "="*50)
        print("SUCCESS! APK generated successfully.")
        print(f"APK Path: {apk_path}")
        print("="*50)
    else:
        print("Error: APK build finished but release APK was not found at the expected path.")

if __name__ == '__main__':
    main()
