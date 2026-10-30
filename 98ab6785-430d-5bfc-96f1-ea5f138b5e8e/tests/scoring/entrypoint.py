"""Isolated interpreter bootstrap: trusted scorer path only, no workspace imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_script import main

if __name__ == "__main__":
    main()
