"""
Simple script to run Nexus AutoDL.
"""

import sys
from pathlib import Path

# Add the current directory to sys.path to ensure the package can be imported
sys.path.insert(0, str(Path(__file__).parent))

from nexus_autodl.main import main

if __name__ == "__main__":
    main()
