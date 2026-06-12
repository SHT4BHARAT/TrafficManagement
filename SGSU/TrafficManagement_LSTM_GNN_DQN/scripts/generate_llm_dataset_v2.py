import subprocess
import sys

if __name__ == "__main__":
    print("[DEPRECATION WARNING] generate_llm_dataset_v2.py is deprecated. Using unified generate_llm_dataset.py --phase-scheme v2.")
    subprocess.run([sys.executable, "generate_llm_dataset.py", "--phase-scheme", "v2"] + sys.argv[1:])
