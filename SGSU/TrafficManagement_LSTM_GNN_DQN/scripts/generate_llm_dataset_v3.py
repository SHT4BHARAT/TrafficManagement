import subprocess
import sys

if __name__ == "__main__":
    print("[DEPRECATION WARNING] generate_llm_dataset_v3.py is deprecated. Using unified generate_llm_dataset.py --phase-scheme v3.")
    subprocess.run([sys.executable, "generate_llm_dataset.py", "--phase-scheme", "v3"] + sys.argv[1:])
