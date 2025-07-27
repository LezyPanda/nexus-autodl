"""
Nexus AutoDL - Automation Script
v0.5.0
"""

import json
import random
import re
from datetime import datetime
from pathlib import Path
from tkinter import (BooleanVar, Button, Checkbutton, DoubleVar, Entry, Frame,
                     Label, Scrollbar, StringVar, Text, Tk, Toplevel,
                     filedialog, Canvas, LabelFrame, colorchooser, IntVar)
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
    has_cv2 = True
except ImportError:
    has_cv2 = False

# --- Utility Functions ---
_INTEGER_PATTERN = re.compile("([0-9]+)")

def _human_sort(key: Path) -> tuple:
    """Sorts file paths naturally (e.g., file1, file2, file10)."""
    return tuple(int(c) if c.isdigit() else c for c in _INTEGER_PATTERN.split(key.name))


class NexusAutoDL:
    """
    The main class for the Nexus AutoDL application.
    Encapsulates all UI, logic, and state management.
    """

    # --- Application Constants ---
    CONFIG_FILE = "config.json"
    CLICK_TOLERANCE = 3  # Pixels to randomize click position for a more human-like interaction.
    
    # --- Dark Mode Theme Colors ---
    BG_COLOR = "#2E2E2E"
    FG_COLOR = "#EAEAEA"
    INPUT_BG_COLOR = "#3C3C3C"
    BUTTON_BG_COLOR = "#555555"
    BUTTON_ACTIVE_BG_COLOR = "#6A6A6A"

    def __init__(self, root: Tk) -> None:
        """Initializes the application, UI, and all necessary components."""
        self.root = root
        self.root.title("Nexus AutoDL (F3 Start/Resume, F4 Pause)")
        self.root.resizable(False, False)
        self.root.config(bg=self.BG_COLOR)

        # --- Core State Variables ---
        self._is_running = False  # Controls the main automation loop.
        self._after_id: Optional[str] = None  # Stores the ID of the pending root.after() job to allow cancellation.

        # --- Tkinter Variables (linked to UI widgets) ---
        self.confidence = DoubleVar()
        self.grayscale = BooleanVar()
        self.min_sleep_seconds = DoubleVar()
        self.max_sleep_seconds = DoubleVar()
        self.templates_path = StringVar()
        self.always_on_top = BooleanVar()
        self.show_visual_feedback = BooleanVar()
        self.feedback_color = StringVar()
        self.feedback_duration = IntVar()

        # --- Window and Data Storage ---
        self.log_window: Optional[Toplevel] = None
        self.log_text_widget: Optional[Text] = None
        self.templates: Dict[str, ImageFile] = {}
        
        self._load_config()
        self._setup_ui()
        self._update_always_on_top()

        self.keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self.keyboard_listener.start()
        self.root.protocol("WM_DELETE_WINDOW", self._terminate_app)

    def _setup_ui(self):
        """Creates and places all GUI widgets using a clean, organized layout."""
        main_frame = Frame(self.root, padx=10, pady=5, bg=self.BG_COLOR)
        main_frame.pack()

        # Define styles for reuse to maintain consistency and reduce code duplication.
        label_style = {"bg": self.BG_COLOR, "fg": self.FG_COLOR}
        entry_style = {"bg": self.INPUT_BG_COLOR, "fg": self.FG_COLOR, "insertbackground": self.FG_COLOR, "bd": 1, "highlightthickness": 0}
        button_style = {"bg": self.BUTTON_BG_COLOR, "fg": self.FG_COLOR, "activebackground": self.BUTTON_ACTIVE_BG_COLOR, "activeforeground": self.FG_COLOR, "bd": 0, "padx": 10}
        check_style = {**label_style, "selectcolor": self.INPUT_BG_COLOR, "activebackground": self.BG_COLOR}
        labelframe_style = {"bg": self.BG_COLOR, "fg": self.FG_COLOR, "padx": 10, "pady": 5}

        # --- Core Settings Frame ---
        core_frame = LabelFrame(main_frame, text="Core Settings", **labelframe_style)
        core_frame.pack(fill="x", expand=True, pady=(0, 5))
        Label(core_frame, text="Templates Directory:", **label_style).grid(row=0, column=0, sticky="w", pady=2)
        Entry(core_frame, state="readonly", textvariable=self.templates_path, readonlybackground=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=1).grid(row=0, column=1, sticky="ew", padx=(5,0))
        Button(core_frame, text="...", command=self._select_folder, **button_style).grid(row=0, column=2, padx=(5, 0))
        core_frame.grid_columnconfigure(1, weight=1)

        # --- Automation Tuning Frame ---
        tuning_frame = LabelFrame(main_frame, text="Automation Tuning", **labelframe_style)
        tuning_frame.pack(fill="x", expand=True, pady=5)
        Label(tuning_frame, text="Confidence:", **label_style).grid(row=0, column=0, sticky="w", pady=2)
        Entry(tuning_frame, textvariable=self.confidence, **entry_style, width=10).grid(row=0, column=1, padx=5)
        Label(tuning_frame, text="Min Sleep (s):", **label_style).grid(row=1, column=0, sticky="w", pady=2)
        Entry(tuning_frame, textvariable=self.min_sleep_seconds, **entry_style, width=10).grid(row=1, column=1, padx=5)
        Label(tuning_frame, text="Max Sleep (s):", **label_style).grid(row=1, column=2, sticky="w", padx=(10, 0))
        Entry(tuning_frame, textvariable=self.max_sleep_seconds, **entry_style, width=10).grid(row=1, column=3, padx=5)

        # --- Display & Behavior Frame ---
        display_frame = LabelFrame(main_frame, text="Display & Behavior", **labelframe_style)
        display_frame.pack(fill="x", expand=True, pady=5)
        Checkbutton(display_frame, text="Grayscale Matching", variable=self.grayscale, **check_style).grid(row=0, column=0, columnspan=2, sticky='w')
        Checkbutton(display_frame, text="Always on Top", variable=self.always_on_top, command=self._update_always_on_top, **check_style).grid(row=0, column=2, columnspan=2, sticky='w', padx=10)
        Checkbutton(display_frame, text="Visual Feedback", variable=self.show_visual_feedback, command=self._toggle_feedback_options, **check_style).grid(row=1, column=0, columnspan=4, sticky='w', pady=(5,0))
        
        self.feedback_options_frame = Frame(display_frame, bg=self.BG_COLOR)
        self.feedback_options_frame.grid(row=2, column=0, columnspan=4, sticky='w', padx=(20, 0))
        Label(self.feedback_options_frame, text="Color:", **label_style).grid(row=0, column=0, sticky="w")
        self.color_swatch = Label(self.feedback_options_frame, text="    ", bg=self.feedback_color.get(), relief="sunken", bd=1)
        self.color_swatch.grid(row=0, column=1, padx=5); self.color_swatch.bind("<Button-1>", self._choose_color)
        Entry(self.feedback_options_frame, textvariable=self.feedback_color, **entry_style, width=10, state="readonly", readonlybackground=self.INPUT_BG_COLOR).grid(row=0, column=2, padx=5)
        Label(self.feedback_options_frame, text="Duration (ms):", **label_style).grid(row=0, column=3, sticky="w", padx=(10,0))
        Entry(self.feedback_options_frame, textvariable=self.feedback_duration, **entry_style, width=10).grid(row=0, column=4, padx=5)

        # --- Action Buttons ---
        action_frame = Frame(main_frame, bg=self.BG_COLOR)
        action_frame.pack(fill="x", expand=True, pady=(15, 5))
        self.create_button = Button(action_frame, text="Create Template", command=self._start_capture_mode, **button_style)
        self.create_button.pack(side="left", expand=True, ipady=5, padx=(0, 5))
        self.start_button = Button(action_frame, text="Start (F3)", command=self._start_handler, **button_style)
        self.start_button.pack(side="left", expand=True, ipady=5)

        self._toggle_feedback_options()

    def _toggle_feedback_options(self):
        """Shows or hides the feedback customization options based on the checkbox state."""
        if self.show_visual_feedback.get():
            self.feedback_options_frame.grid(row=2, column=0, columnspan=4, sticky='w', padx=(20, 0), pady=5)
        else:
            self.feedback_options_frame.grid_forget()

    def _choose_color(self, event=None):
        """Opens a color chooser and updates the feedback color."""
        _, color_hex = colorchooser.askcolor(parent=self.root, initialcolor=self.feedback_color.get())
        if color_hex:
            self.feedback_color.set(color_hex); self.color_swatch.config(bg=color_hex)

    def _show_feedback_box(self, box):
        """Creates a temporary, border-only window to provide visual feedback."""
        feedback_window = Toplevel(self.root)
        feedback_window.overrideredirect(True)
        feedback_window.geometry(f'{box.width}x{box.height}+{box.left}+{box.top}')
        # This technique uses a 'magic' color that the OS is told to render as transparent.
        feedback_window.config(bg='snow')
        feedback_window.wm_attributes("-transparentcolor", 'snow')
        feedback_window.attributes("-topmost", True)
        border_frame = Frame(feedback_window, highlightbackground=self.feedback_color.get(), highlightthickness=3, bg='snow')
        border_frame.pack(fill="both", expand=True)
        # Forcing Tkinter to draw the window immediately is crucial for the animation to be visible before the click.
        self.root.update_idletasks()
        return feedback_window

    def _start_capture_mode(self):
        """Hides the main window and creates a fullscreen overlay for screen capture."""
        self.root.withdraw()
        self.capture_window = Toplevel(self.root)
        self.capture_window.attributes("-fullscreen", True); self.capture_window.attributes("-alpha", 0.3); self.capture_window.attributes("-topmost", True)
        self.capture_canvas = Canvas(self.capture_window, cursor="cross", bg="grey"); self.capture_canvas.pack(fill="both", expand=True)
        self.rect, self.start_x, self.start_y = None, None, None
        self.capture_canvas.bind("<ButtonPress-1>", self._on_capture_press); self.capture_canvas.bind("<B1-Motion>", self._on_capture_drag); self.capture_canvas.bind("<ButtonRelease-1>", self._on_capture_release)

    def _on_capture_press(self, event):
        self.start_x, self.start_y = self.capture_canvas.canvasx(event.x), self.capture_canvas.canvasy(event.y)
        self.rect = self.capture_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def _on_capture_drag(self, event):
        cur_x, cur_y = self.capture_canvas.canvasx(event.x), self.capture_canvas.canvasy(event.y)
        self.capture_canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def _on_capture_release(self, event):
        end_x, end_y = self.capture_canvas.canvasx(event.x), self.capture_canvas.canvasy(event.y)
        self.capture_window.destroy()
        x1, y1, x2, y2 = min(self.start_x, end_x), min(self.start_y, end_y), max(self.start_x, end_x), max(self.start_y, end_y)
        width, height = x2 - x1, y2 - y1
        if width > 10 and height > 10:
            try:
                region_tuple = (int(x1), int(y1), int(width), int(height))
                img = pyautogui.screenshot(region=region_tuple)
                template_dir = Path(self.templates_path.get()); template_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = template_dir / f"template_{timestamp}.png"
                img.save(save_path)
                messagebox.showinfo("Success", f"Template saved to:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save template: {e}")
        self.root.deiconify()
    
    def _log(self, message: str, level: str = "INFO"):
        """Logs a message to the text widget in the log window."""
        if not self.log_text_widget: return
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text_widget.insert("end", f"[{timestamp}][{level}] {message}\n"); self.log_text_widget.see("end")

    def _load_config(self):
        """Loads all settings from the config file, with sane defaults."""
        try:
            with open(self.CONFIG_FILE, "r") as f: config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): config = {}
        self.confidence.set(config.get("confidence", 0.7)); self.grayscale.set(config.get("grayscale", True))
        self.min_sleep_seconds.set(config.get("min_sleep", 1.0)); self.max_sleep_seconds.set(config.get("max_sleep", 5.0))
        self.templates_path.set(config.get("templates_path", "templates")); self.always_on_top.set(config.get("always_on_top", False))
        self.show_visual_feedback.set(config.get("show_visual_feedback", False)); self.feedback_color.set(config.get("feedback_color", "#00FF00"))
        self.feedback_duration.set(config.get("feedback_duration", 400))

    def _save_config(self):
        """Saves all current settings to the config file."""
        settings = {"confidence": self.confidence.get(), "grayscale": self.grayscale.get(), "min_sleep": self.min_sleep_seconds.get(), "max_sleep": self.max_sleep_seconds.get(), "templates_path": self.templates_path.get(), "always_on_top": self.always_on_top.get(), "show_visual_feedback": self.show_visual_feedback.get(), "feedback_color": self.feedback_color.get(), "feedback_duration": self.feedback_duration.get()}
        with open(self.CONFIG_FILE, "w") as f: json.dump(settings, f, indent=4)

    def _validate_inputs(self) -> bool:
        """Validates all user-configurable fields before starting."""
        try:
            conf, min_s, max_s = self.confidence.get(), self.min_sleep_seconds.get(), self.max_sleep_seconds.get()
            if not (0.0 <= conf <= 1.0): messagebox.showerror("Invalid Input", "Confidence must be between 0.0 and 1.0."); return False
            if min_s < 0 or max_s < 0: messagebox.showerror("Invalid Input", "Sleep times cannot be negative."); return False
            if min_s > max_s: messagebox.showerror("Invalid Input", "Min sleep must not be greater than Max sleep."); return False
            if not Path(self.templates_path.get()).exists(): messagebox.showerror("Invalid Path", f"The specified templates directory does not exist:\n{self.templates_path.get()}"); return False
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
        if self.log_window and self.log_window.winfo_exists(): self.log_window.attributes("-topmost", is_on_top)

    def _start_handler(self):
        """Handles both starting the process for the first time and resuming it."""
        if self._is_running: return
        if not self._validate_inputs(): return
        self._is_running = True; self.start_button.config(state="disabled", text="Running...")
        if self.log_window is None:
            self._show_log_window(); self._load_templates(); self._log("Process started. Starting search loop...")
        else:
            self._log("Process resumed."); self.root.withdraw()
        self._match_loop()

    def _pause_handler(self):
        """Pauses the matching process and shows the config window."""
        if not self._is_running: return
        self._is_running = False
        if self._after_id: self.root.after_cancel(self._after_id)
        self.start_button.config(state="normal", text="Resume (F3)")
        self.root.deiconify(); self._log("Process paused. Press F3 to resume.", "WARN")

    def _load_templates(self):
        """Loads all template images from the specified directory."""
        self.templates.clear()
        for path in sorted(Path(self.templates_path.get()).iterdir(), key=_human_sort):
            try:
                img = open_image(path); self.templates[str(path)] = img.copy(); img.close()
                self._log(f"Loaded template: {path.name}")
            except (IsADirectoryError, UnidentifiedImageError): pass

    def _match_loop(self):
        """The main, non-blocking application loop that drives the automation."""
        if not self._is_running: return
        self._perform_match()
        sleep_interval = random.uniform(self.min_sleep_seconds.get(), self.max_sleep_seconds.get())
        self._log(f"Waiting for {sleep_interval:.2f} seconds.")
        self._after_id = self.root.after(int(sleep_interval * 1000), self._match_loop)

    def _perform_click_action(self, box, path_name):
        """Helper function to contain all the logic for a click action."""
        center_x, center_y = pyautogui.center(box)
        click_x = center_x + random.randint(-self.CLICK_TOLERANCE, self.CLICK_TOLERANCE)
        click_y = center_y + random.randint(-self.CLICK_TOLERANCE, self.CLICK_TOLERANCE)
        original_pos = pyautogui.position(); pyautogui.click(click_x, click_y); pyautogui.moveTo(original_pos)
        self._log(f"Clicked {path_name} at ({click_x}, {click_y})", "INFO")

    def _perform_match(self):
        """Performs one cycle of searching for any template and handles the result."""
        if not self.templates:
            self._log("No valid templates loaded. Stopping.", "FATAL"); self._terminate_app(); return
        search_kwargs: Dict[str, Any] = {"grayscale": self.grayscale.get()}
        if has_cv2: search_kwargs["confidence"] = self.confidence.get()
        screenshot = pyautogui.screenshot()
        for path_str, image in self.templates.items():
            path_name = Path(path_str).name
            self._log(f"Attempting to find {path_name}.")
            try:
                box = pyautogui.locate(image, screenshot, **search_kwargs)
                if box:
                    self._handle_found_match(box, path_name)
                    return
            except pyautogui.PyAutoGUIException as e:
                self._log(f"Search error for {path_name}: {e}", "WARN")

    def _handle_found_match(self, box, path_name):
        """Centralized logic for when a template is found to manage feedback and clicks."""
        if self.show_visual_feedback.get():
            feedback_box = self._show_feedback_box(box)
            # The click action is now scheduled to run AFTER the feedback animation is over.
            # This is critical to prevent the click from hitting the feedback window itself.
            self.root.after(self.feedback_duration.get(), lambda: (
                feedback_box.destroy(), self._perform_click_action(box, path_name)
            ))
        else:
            self._perform_click_action(box, path_name)

    def _show_log_window(self):
        """Hides the main window and creates the log console."""
        self.root.withdraw()
        self.log_window = Toplevel(self.root)
        self.log_window.title("Log Console"); self.log_window.protocol("WM_DELETE_WINDOW", self._terminate_app); self.log_window.config(bg=self.BG_COLOR)
        self._update_always_on_top()
        frame = Frame(self.log_window, bg=self.BG_COLOR); frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.log_text_widget = Text(frame, height=20, width=100, wrap="word", bg=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=0, highlightthickness=0); self.log_text_widget.pack(side="left", fill="both", expand=True)
        scrollbar = Scrollbar(frame, command=self.log_text_widget.yview, bg=self.BG_COLOR, troughcolor=self.INPUT_BG_COLOR, bd=0, activebackground=self.BUTTON_ACTIVE_BG_COLOR); scrollbar.pack(side="right", fill="y")
        self.log_text_widget.config(yscrollcommand=scrollbar.set)
        if not has_cv2:
            self._log("Note: For confidence-based matching, install OpenCV via: pip install opencv-python", "WARN")

    def _terminate_app(self):
        """Cleanly saves config, stops all loops and listeners, and exits the application."""
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
