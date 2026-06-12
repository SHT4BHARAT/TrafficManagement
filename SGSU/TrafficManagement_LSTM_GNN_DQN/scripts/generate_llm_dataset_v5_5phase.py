import subprocess
import sys

if __name__ == "__main__":
    print("[DEPRECATION WARNING] generate_llm_dataset_v5_5phase.py is deprecated. Using unified generate_llm_dataset.py --phase-scheme v5_5phase.")
    subprocess.run([sys.executable, "generate_llm_dataset.py", "--phase-scheme", "v5_5phase"] + sys.argv[1:])
