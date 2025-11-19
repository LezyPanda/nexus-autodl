"""
Constants used throughout the Nexus AutoDL application.
"""

class AppConstants:
    VERSION = "v0.6.3"
    CONFIG_FILE = "config.json"
    CLICK_TOLERANCE = 3
    MIN_CAPTURE_SIZE = 10
    TRANSPARENT_COLOR = "#010203"
    CACHE_SIZE = 50
    SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
    TOOLTIP_DELAY = 400
    FEEDBACK_WINDOW_DELAY = 100
    LOG_WINDOW_SIZE = "800x400"
    PROFILE_MANAGER_SIZE = "650x500"
    INVALID_FILENAME_CHARS = {'/', '\\', ':', '*', '?', '"', '<', '>', '|'}
