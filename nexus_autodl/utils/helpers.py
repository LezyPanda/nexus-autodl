"""
Helper functions for Nexus AutoDL.
"""

import re
from pathlib import Path
from typing import Tuple, Union
from ..constants import AppConstants

INTEGER_PATTERN = re.compile(r"([0-9]+)")

def human_sort_key(path: Path) -> Tuple[Union[int, str], ...]:
    """
    Sorts paths in a human-readable way (e.g., 1, 2, 10 instead of 1, 10, 2).
    """
    return tuple(
        int(c) if c.isdigit() else c.lower() 
        for c in INTEGER_PATTERN.split(path.name)
    )

def safe_path_operation(func):
    """
    Decorator to safely handle path operations.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (OSError, IOError, PermissionError) as e:
            print(f"Path operation failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in path operation: {e}")
            return None
    return wrapper

def validate_filename(filename: str) -> bool:
    """
    Validates that a filename does not contain invalid characters.
    """
    return not any(char in filename for char in AppConstants.INVALID_FILENAME_CHARS)
