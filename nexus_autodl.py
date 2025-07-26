"""
Nexus AutoDL - Automation Script
Version 0.4.1

Added comments to explain the core logic,
making the code easier to understand and maintain.
"""

import json
import random
import re
from datetime import datetime
from pathlib import Path
from tkinter import (BooleanVar, Button, Checkbutton, DoubleVar, Entry, Frame,
                     Label, Scrollbar, StringVar, Text, Tk, Toplevel,
                     filedialog, Canvas)
from tkinter import messagebox
from typing import Any, Dict, Optional

# --- Dependency Check ---
try:
    from pynput import keyboard
    import pyautogui
    from PIL import UnidentifiedImageError, Image
    from PIL.Image import open as open_image
    from PIL.ImageFile import ImageFile
except ImportError as e:
    print(f"Error: A critical library is missing: {e.name}.")
    print("Please, run in your terminal: pip install pyautogui Pillow pynput")
    exit()

try:
    import cv2
    del cv2
    has_cv2 = True
except ImportError:
    has_cv2 = False

# --- Constants ---
CONFIG_FILE = "config.json"
CLICK_TOLERANCE = 3

# --- Utility Functions ---
_INTEGER_PATTERN = re.compile("([0-9]+)")

def _human_sort(key: Path) -> tuple:
    return tuple(int(c) if c.isdigit() else c for c in _INTEGER_PATTERN.split(key.name))


class NexusAutoDL:
    """The main class for the Nexus AutoDL application."""

    # --- Dark Mode Colors ---
    BG_COLOR = "#2E2E2E"
    FG_COLOR = "#EAEAEA"
    INPUT_BG_COLOR = "#3C3C3C"
    BUTTON_BG_COLOR = "#555555"
    BUTTON_ACTIVE_BG_COLOR = "#6A6A6A"

    def __init__(self, root: Tk) -> None:
        """Initializes the application, UI, and all necessary variables."""
        self.root = root
        self.root.title("Nexus AutoDL (F3 Start/Resume, F4 Pause)")
        self.root.resizable(False, False)
        self.root.config(bg=self.BG_COLOR)

        # Core state variables
        self._is_running = False
        self._after_id: Optional[str] = None # Stores the ID of the pending root.after() job

        # Tkinter variables linked to UI widgets
        self.confidence = DoubleVar()
        self.grayscale = BooleanVar()
        self.min_sleep_seconds = DoubleVar()
        self.max_sleep_seconds = DoubleVar()
        self.templates_path = StringVar()
        self.always_on_top = BooleanVar()

        # Window and data storage
        self.log_window: Optional[Toplevel] = None
        self.log_text_widget: Optional[Text] = None
        self.templates: Dict[str, ImageFile] = {}
        
        self._load_config() # Load first to populate variables
        self._setup_ui()    # Then build UI with loaded values
        self._update_always_on_top() # Apply initial 'Always on Top' state

        # Start listening for global hotkeys
        self.keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self.keyboard_listener.start()
        # Ensure clean exit
        self.root.protocol("WM_DELETE_WINDOW", self._terminate_app)

    def _setup_ui(self):
        """Creates and places all GUI widgets with dark mode styling."""
        input_frame = Frame(self.root, padx=10, pady=10, bg=self.BG_COLOR)
        input_frame.pack()

        # Define styles for reuse
        label_style = {"bg": self.BG_COLOR, "fg": self.FG_COLOR}
        entry_style = {"bg": self.INPUT_BG_COLOR, "fg": self.FG_COLOR, "insertbackground": self.FG_COLOR, "bd": 1, "highlightthickness": 0}
        button_style = {"bg": self.BUTTON_BG_COLOR, "fg": self.FG_COLOR, "activebackground": self.BUTTON_ACTIVE_BG_COLOR, "activeforeground": self.FG_COLOR, "bd": 0}
        check_style = {**label_style, "selectcolor": self.INPUT_BG_COLOR, "activebackground": self.BG_COLOR}

        # --- Grid Layout ---
        Label(input_frame, text="Confidence:", **label_style).grid(row=0, column=0, sticky="w", pady=2)
        Entry(input_frame, textvariable=self.confidence, **entry_style).grid(row=0, column=1)
        Label(input_frame, text="Min sleep seconds:", **label_style).grid(row=1, column=0, sticky="w", pady=2)
        Entry(input_frame, textvariable=self.min_sleep_seconds, **entry_style).grid(row=1, column=1)
        Label(input_frame, text="Max sleep seconds:", **label_style).grid(row=2, column=0, sticky="w", pady=2)
        Entry(input_frame, textvariable=self.max_sleep_seconds, **entry_style).grid(row=2, column=1)
        Label(input_frame, text="Templates directory:", **label_style).grid(row=3, column=0, sticky="w", pady=2)
        Entry(input_frame, state="readonly", textvariable=self.templates_path, readonlybackground=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=1).grid(row=3, column=1)
        Button(input_frame, text="...", command=self._select_folder, **button_style).grid(row=3, column=2, padx=(5, 0))
        
        # Checkboxes are placed in their own frame for better alignment
        check_frame = Frame(input_frame, bg=self.BG_COLOR)
        check_frame.grid(row=4, column=0, columnspan=3, sticky="w", pady=5)
        Checkbutton(check_frame, text="Grayscale", variable=self.grayscale, **check_style).pack(side="left")
        Checkbutton(check_frame, text="Always on Top", variable=self.always_on_top, command=self._update_always_on_top, **check_style).pack(side="left", padx=10)
        
        # Action buttons are in a separate frame to allow side-by-side packing
        action_frame = Frame(input_frame, bg=self.BG_COLOR)
        action_frame.grid(row=5, column=0, columnspan=3, pady=(10, 0), sticky="ew")
        
        self.create_button = Button(action_frame, text="Create Template", command=self._start_capture_mode, **button_style)
        self.create_button.pack(side="left", expand=True, ipady=5, padx=(0, 5))

        self.start_button = Button(action_frame, text="Start (F3)", command=self._start_handler, **button_style)
        self.start_button.pack(side="left", expand=True, ipady=5)

    # --- Integrated Template Creation ---
    def _start_capture_mode(self):
        """Hides the main window and creates a fullscreen overlay for screen capture."""
        self.root.withdraw() # Hide main window to allow capturing any part of the screen
        
        # Create a new, fullscreen, semi-transparent window
        self.capture_window = Toplevel(self.root)
        self.capture_window.attributes("-fullscreen", True)
        self.capture_window.attributes("-alpha", 0.3) # Transparency
        self.capture_window.attributes("-topmost", True)
        
        # The canvas is where the user will draw the rectangle
        self.capture_canvas = Canvas(self.capture_window, cursor="cross", bg="grey")
        self.capture_canvas.pack(fill="both", expand=True)

        self.rect = None # To store the rectangle ID
        self.start_x = None
        self.start_y = None

        # Bind mouse events to the canvas
        self.capture_canvas.bind("<ButtonPress-1>", self._on_capture_press)
        self.capture_canvas.bind("<B1-Motion>", self._on_capture_drag)
        self.capture_canvas.bind("<ButtonRelease-1>", self._on_capture_release)

    def _on_capture_press(self, event):
        """Stores starting coordinates when the mouse is clicked."""
        self.start_x = self.capture_canvas.canvasx(event.x)
        self.start_y = self.capture_canvas.canvasy(event.y)
        self.rect = self.capture_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def _on_capture_drag(self, event):
        """Updates the rectangle's dimensions as the mouse is dragged."""
        cur_x = self.capture_canvas.canvasx(event.x)
        cur_y = self.capture_canvas.canvasy(event.y)
        self.capture_canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def _on_capture_release(self, event):
        """Captures the selected screen region when the mouse is released."""
        end_x = self.capture_canvas.canvasx(event.x)
        end_y = self.capture_canvas.canvasy(event.y)
        
        self.capture_window.destroy() # Close the overlay immediately

        # Ensure correct coordinates regardless of drag direction
        x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
        
        width = x2 - x1
        height = y2 - y1

        # Only save if the selection is reasonably large
        if width > 10 and height > 10:
            try:
                # CRITICAL FIX: Convert all region values to integers to prevent pyautogui errors.
                region_tuple = (int(x1), int(y1), int(width), int(height))
                img = pyautogui.screenshot(region=region_tuple)
                
                template_dir = Path(self.templates_path.get())
                template_dir.mkdir(exist_ok=True) # Create folder if it doesn't exist
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = template_dir / f"template_{timestamp}.png"
                img.save(save_path)
                messagebox.showinfo("Success", f"Template saved to:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save template: {e}")

        self.root.deiconify() # Show the main window again
    
    # --- Core Application Logic ---
    
    def _log(self, message: str, level: str = "INFO"):
        """Logs a message to the text widget in the log window."""
        if not self.log_text_widget: return
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text_widget.insert("end", f"[{timestamp}][{level}] {message}\n")
        self.log_text_widget.see("end") # Auto-scroll to the bottom

    def _load_config(self):
        """Loads all settings from the config file, with sane defaults."""
        try:
            with open(CONFIG_FILE, "r") as f: config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): config = {} # Use defaults if file not found or invalid
        
        # .get() is used to provide a default value if the key is missing
        self.confidence.set(config.get("confidence", 0.7))
        self.grayscale.set(config.get("grayscale", True))
        self.min_sleep_seconds.set(config.get("min_sleep", 1.0))
        self.max_sleep_seconds.set(config.get("max_sleep", 5.0))
        self.templates_path.set(config.get("templates_path", "templates"))
        self.always_on_top.set(config.get("always_on_top", False))

    def _save_config(self):
        """Saves all current settings to the config file."""
        settings = {
            "confidence": self.confidence.get(),
            "grayscale": self.grayscale.get(),
            "min_sleep": self.min_sleep_seconds.get(),
            "max_sleep": self.max_sleep_seconds.get(),
            "templates_path": self.templates_path.get(),
            "always_on_top": self.always_on_top.get()
        }
        with open(CONFIG_FILE, "w") as f: json.dump(settings, f, indent=4)

    def _validate_inputs(self) -> bool:
        """Validates all user-configurable fields before starting."""
        try:
            conf, min_s, max_s = self.confidence.get(), self.min_sleep_seconds.get(), self.max_sleep_seconds.get()
            if not (0.0 <= conf <= 1.0): messagebox.showerror("Invalid Input", "Confidence must be between 0.0 and 1.0."); return False
            if min_s < 0 or max_s < 0: messagebox.showerror("Invalid Input", "Sleep times cannot be negative."); return False
            if min_s > max_s: messagebox.showerror("Invalid Input", "Min sleep must not be greater than Max sleep."); return False
            if not Path(self.templates_path.get()).exists(): messagebox.showerror("Invalid Path", "The specified templates directory does not exist."); return False
            return True
        except Exception:
            messagebox.showerror("Invalid Input", "Please ensure all fields contain valid numbers."); return False

    def _on_press(self, key):
        """Global hotkey handler."""
        if key == keyboard.Key.f3: self._start_handler()
        elif key == keyboard.Key.f4: self._pause_handler()

    def _select_folder(self):
        """Opens a dialog to select the template folder."""
        path = filedialog.askdirectory(title="Select Templates Folder")
        if path: self.templates_path.set(path)

    def _update_always_on_top(self):
        """Applies the always-on-top state to the root and log window."""
        is_on_top = self.always_on_top.get()
        self.root.attributes("-topmost", is_on_top)
        # Also apply to log window if it exists
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.attributes("-topmost", is_on_top)

    def _start_handler(self):
        """Handles both starting the process for the first time and resuming it."""
        if self._is_running: return # Prevent starting if already running
        
        # Re-validate settings on every start/resume in case they were changed
        if not self._validate_inputs(): return

        self._is_running = True
        self.start_button.config(state="disabled", text="Running...")

        if self.log_window is None: # First start
            self._show_log_window()
            self._load_templates()
            self._log("Process started. Starting search loop...")
        else: # Resuming from pause
            self._log("Process resumed.")
            self.root.withdraw() # Hide the config window again on resume
        
        self._match_loop()

    def _pause_handler(self):
        """Pauses the matching process."""
        if not self._is_running: return # Prevent pausing if not running

        self._is_running = False
        if self._after_id: self.root.after_cancel(self._after_id) # Cancel any pending match job
        
        self.start_button.config(state="normal", text="Resume (F3)")
        self.root.deiconify() # Show the config window on pause to allow changes
        self._log("Process paused. Press F3 to resume.", "WARN")

    def _load_templates(self):
        """Loads all template images from the specified directory."""
        self.templates.clear()
        for path in sorted(Path(self.templates_path.get()).iterdir(), key=_human_sort):
            try:
                img = open_image(path)
                self.templates[str(path)] = img.copy() # .copy() prevents file handle issues
                img.close()
                self._log(f"Loaded template: {path.name}")
            except (IsADirectoryError, UnidentifiedImageError): pass # Ignore folders and non-images

    def _match_loop(self):
        """The main, non-blocking application loop, powered by root.after()."""
        if not self._is_running: return # Stop the loop if paused
        
        self._perform_match() # Do the work
        
        # Schedule the next run
        sleep_interval = random.uniform(self.min_sleep_seconds.get(), self.max_sleep_seconds.get())
        self._log(f"Waiting for {sleep_interval:.2f} seconds.")
        self._after_id = self.root.after(int(sleep_interval * 1000), self._match_loop)

    def _perform_match(self):
        """Performs one cycle of searching and clicking."""
        search_kwargs: Dict[str, Any] = {"grayscale": self.grayscale.get()}
        if has_cv2: search_kwargs["confidence"] = self.confidence.get()
        if not self.templates:
            self._log("No valid templates loaded. Stopping.", "FATAL")
            self._terminate_app(); return

        screenshot = pyautogui.screenshot()
        for path_str, image in self.templates.items():
            path_name = Path(path_str).name
            self._log(f"Attempting to find {path_name}.")
            try:
                box = pyautogui.locate(image, screenshot, **search_kwargs)
                if box:
                    center_x, center_y = pyautogui.center(box)
                    click_x = center_x + random.randint(-CLICK_TOLERANCE, CLICK_TOLERANCE)
                    click_y = center_y + random.randint(-CLICK_TOLERANCE, CLICK_TOLERANCE)
                    
                    # Save mouse position, click, and then return the mouse
                    original_pos = pyautogui.position()
                    pyautogui.click(click_x, click_y)
                    pyautogui.moveTo(original_pos)
                    
                    self._log(f"Clicked {path_name} at ({click_x}, {click_y}) and returned mouse.", "INFO")
                    return # Exit the search for this cycle after finding a match
            except pyautogui.PyAutoGUIException as e:
                self._log(f"Search error for {path_name}: {e}", "WARN")

    def _show_log_window(self):
        """Hides the main window and creates the log console."""
        self.root.withdraw()
        self.log_window = Toplevel(self.root)
        self.log_window.title("Log Console")
        self.log_window.protocol("WM_DELETE_WINDOW", self._terminate_app)
        self.log_window.config(bg=self.BG_COLOR)
        self._update_always_on_top() # Apply on-top state when the window is created

        frame = Frame(self.log_window, bg=self.BG_COLOR)
        frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.log_text_widget = Text(frame, height=20, width=100, wrap="word", bg=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=0, highlightthickness=0)
        self.log_text_widget.pack(side="left", fill="both", expand=True)
        scrollbar = Scrollbar(frame, command=self.log_text_widget.yview, bg=self.BG_COLOR, troughcolor=self.INPUT_BG_COLOR, bd=0, activebackground=self.BUTTON_ACTIVE_BG_COLOR)
        scrollbar.pack(side="right", fill="y")
        self.log_text_widget.config(yscrollcommand=scrollbar.set)

    def _terminate_app(self):
        """Cleanly saves config, stops all loops and listeners, and exits."""
        self._save_config()
        self._is_running = False
        if self._after_id: self.root.after_cancel(self._after_id)
        if self.keyboard_listener.is_alive(): self.keyboard_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    main_root = Tk()
    app = NexusAutoDL(main_root)
    try:
        main_root.mainloop()
    except KeyboardInterrupt:
        # This handles closing the app with Ctrl+C in the terminal
        app._terminate_app()
