"""Usage: python3 plearun_cli.py REPORT RECORDS_DIR > findings.json"""
import sys

from plearun.pipeline import main

if __name__ == "__main__":
    sys.exit(main())
