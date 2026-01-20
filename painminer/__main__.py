"""
Entry point for running painminer as a module.

Usage: python -m painminer [command] [options]
"""

import sys
from painminer.cli import main

if __name__ == "__main__":
    sys.exit(main())
