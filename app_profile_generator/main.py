import sys
from pathlib import Path


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app_profile_generator.cli.main import main


if __name__ == "__main__":
    sys.exit(main())
