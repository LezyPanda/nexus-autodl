"""
Main entry point for Nexus AutoDL.
"""

import sys
from tkinter import Tk

try:
    from pynput import keyboard
    import pyautogui
    from PIL import Image
except ImportError as e:
    print(f"Error: A critical library is missing: {e.name}.")
    print("Please, run in your terminal: pip install pyautogui Pillow pynput")
    sys.exit(1)

from .ui.app_window import NexusAutoDL

def main():
    try:
        root = Tk()
        app = NexusAutoDL(root)
        root.mainloop()
        
    except KeyboardInterrupt:
        print("Application interrupted by user")
        if 'app' in locals():
            app._terminate_app()
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if 'root' in locals():
                root.destroy()
        except:
            pass

if __name__ == "__main__":
    main()
