#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add parent directory to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hue_portal.hue_portal.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
if __name__ == "__main__":
    main()

