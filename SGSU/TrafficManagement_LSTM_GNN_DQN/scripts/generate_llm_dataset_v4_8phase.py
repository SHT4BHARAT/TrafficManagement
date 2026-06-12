import subprocess
import sys

if __name__ == "__main__":
    print("[DEPRECATION WARNING] generate_llm_dataset_v4_8phase.py is deprecated. Using unified generate_llm_dataset.py --phase-scheme v4_8phase.")
    subprocess.run([sys.executable, "generate_llm_dataset.py", "--phase-scheme", "v4_8phase"] + sys.argv[1:])
