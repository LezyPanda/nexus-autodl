"""
Nexus AutoDL - Automation Script
v0.6.0
"""

import json
import random
import re
import shutil
from datetime import datetime
from pathlib import Path
from tkinter import (BooleanVar, Button, Checkbutton, DoubleVar, Entry, Frame,
                     Label, Listbox, Scrollbar, StringVar, Text, Tk, Toplevel,
                     filedialog, Canvas, LabelFrame, colorchooser, IntVar)
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Dict, Optional

# --- Dependency Check ---
try:
    from pynput import keyboard
    import pyautogui
    from PIL import UnidentifiedImageError, Image
    from PIL.Image import open as open_image
except ImportError as e:
    print(f"Error: A critical library is missing: {e.name}.")
    print("Please, run in your terminal: pip install pyautogui Pillow pynput")
    exit()

try:
    import cv2
    has_cv2 = True
except ImportError:
    has_cv2 = False

# --- Utility Functions & Classes ---
_INTEGER_PATTERN = re.compile("([0-9]+)")

def _human_sort(key: Path) -> tuple:
    return tuple(
        int(c) if c.isdigit() else c for c in _INTEGER_PATTERN.split(key.name)
    )

class Tooltip:
    """A reusable class to create tooltips for any tkinter widget."""
    def __init__(self, widget, text: str, delay: int = 400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window: Optional[Toplevel] = None
        self.id: Optional[str] = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None): self.schedule()
    def leave(self, event=None): self.cancel(); self.hide_tooltip()
    def schedule(self): self.cancel(); self.id = self.widget.after(self.delay, self.show_tooltip)
    def cancel(self):
        if self.id: self.widget.after_cancel(self.id); self.id = None
    def show_tooltip(self):
        if self.tooltip_window: return
        x, y = self.widget.winfo_pointerxy()
        self.tooltip_window = Toplevel(self.widget)
        self.tooltip_window.overrideredirect(True)
        self.tooltip_window.geometry(f"+{x+20}+{y+10}")
        if self.widget.winfo_toplevel().attributes("-topmost"):
            self.tooltip_window.attributes("-topmost", True)
        label = Label(self.tooltip_window, text=self.text, justify='left', background="#1E1E1E", foreground="#EAEAEA", relief='solid', borderwidth=1, wraplength=300, padx=8, pady=5)
        label.pack(ipadx=1)
    def hide_tooltip(self):
        if self.tooltip_window: self.tooltip_window.destroy(); self.tooltip_window = None


class ProfileManagerWindow(Toplevel):
    """A dedicated window for creating, renaming, and deleting profiles."""
    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.parent_app = parent_app
        self.transient(parent_app.root)
        self.title("Profile Manager")
        self.config(bg=parent_app.BG_COLOR)
        self.resizable(False, False)
        self.grab_set()
        self._setup_ui()
        self._populate_listbox()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        parent = self.parent_app.root
        parent_x, parent_y = parent.winfo_x(), parent.winfo_y()
        parent_width, parent_height = parent.winfo_width(), parent.winfo_height()
        my_width, my_height = self.winfo_width(), self.winfo_height()
        pos_x = (parent_width // 2) - (my_width // 2) + parent_x
        pos_y = (parent_height // 2) - (my_height // 2) + parent_y
        self.geometry(f"+{pos_x}+{pos_y}")

    def _setup_ui(self):
        main_frame = Frame(self, padx=10, pady=10, bg=self.parent_app.BG_COLOR); main_frame.pack(fill="both", expand=True)
        dir_frame = Frame(main_frame, bg=self.parent_app.BG_COLOR); dir_frame.pack(fill="x", pady=(0, 10))
        Label(dir_frame, text="Profiles Directory:", bg=self.parent_app.BG_COLOR, fg=self.parent_app.FG_COLOR).pack(side="left")
        Entry(dir_frame, textvariable=self.parent_app.profiles_root_path, state="readonly", readonlybackground=self.parent_app.INPUT_BG_COLOR, fg=self.parent_app.FG_COLOR, bd=1).pack(side="left", fill="x", expand=True, padx=5)
        Button(dir_frame, text="...", command=self._select_profiles_root, bg=self.parent_app.BUTTON_BG_COLOR, fg=self.parent_app.FG_COLOR, bd=0, padx=10).pack(side="left")
        list_frame = Frame(main_frame); list_frame.pack(fill="both", expand=True)
        self.profile_listbox = Listbox(list_frame, bg=self.parent_app.INPUT_BG_COLOR, fg=self.parent_app.FG_COLOR, bd=0, highlightthickness=0, selectbackground=self.parent_app.BUTTON_ACTIVE_BG_COLOR, exportselection=False)
        self.profile_listbox.pack(side="left", fill="both", expand=True)
        self.profile_listbox.bind("<Double-Button-1>", self._set_active_profile)
        scrollbar = Scrollbar(list_frame, command=self.profile_listbox.yview); scrollbar.pack(side="right", fill="y")
        self.profile_listbox.config(yscrollcommand=scrollbar.set)
        button_frame = Frame(main_frame, bg=self.parent_app.BG_COLOR); button_frame.pack(fill="x", pady=(10, 0))
        button_style = {"bg": self.parent_app.BUTTON_BG_COLOR, "fg": self.parent_app.FG_COLOR, "activebackground": self.parent_app.BUTTON_ACTIVE_BG_COLOR, "bd": 0, "padx": 10}
        Button(button_frame, text="New", command=self._create_profile, **button_style).pack(side="left", expand=True, ipady=5)
        Button(button_frame, text="Rename", command=self._rename_profile, **button_style).pack(side="left", expand=True, ipady=5, padx=5)
        Button(button_frame, text="Delete", command=self._delete_profile, **button_style).pack(side="left", expand=True, ipady=5)

    def _populate_listbox(self):
        self.profile_listbox.delete(0, 'end')
        profiles = sorted(self.parent_app.get_profiles())
        for i, profile in enumerate(profiles):
            self.profile_listbox.insert('end', profile)
            if profile == self.parent_app.active_profile.get():
                self.profile_listbox.selection_set(i); self.profile_listbox.activate(i); self.profile_listbox.see(i)
    
    def _select_profiles_root(self):
        path = filedialog.askdirectory(title="Select Profiles Root Directory", parent=self)
        if path:
            self.parent_app.profiles_root_path.set(path)
            self.parent_app._update_profile_list(); self._populate_listbox()

    def _create_profile(self):
        self.parent_app._create_new_profile(parent_window=self); self._populate_listbox()

    def _rename_profile(self):
        selected_indices = self.profile_listbox.curselection()
        if not selected_indices: messagebox.showwarning("No Selection", "Please select a profile to rename.", parent=self); return
        old_name = self.profile_listbox.get(selected_indices[0])
        new_name = simpledialog.askstring("Rename Profile", f"Enter a new name for '{old_name}':", parent=self)
        if not new_name or not new_name.strip() or new_name == old_name: return
        root_path = Path(self.parent_app.profiles_root_path.get())
        old_path, new_path = root_path / old_name, root_path / new_name
        if new_path.exists(): messagebox.showerror("Error", f"A profile named '{new_name}' already exists.", parent=self); return
        try:
            old_path.rename(new_path)
            self.parent_app._rename_profile_config(old_name, new_name)
            self.parent_app._update_profile_list(); self._populate_listbox()
            for i in range(self.profile_listbox.size()):
                if self.profile_listbox.get(i) == new_name:
                    self.profile_listbox.selection_set(i); self.profile_listbox.activate(i); break
        except Exception as e: messagebox.showerror("Error", f"Could not rename profile: {e}", parent=self)

    def _delete_profile(self):
        selected_indices = self.profile_listbox.curselection()
        if not selected_indices: messagebox.showwarning("No Selection", "Please select a profile to delete.", parent=self); return
        profile_to_delete = self.profile_listbox.get(selected_indices[0])
        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete the profile '{profile_to_delete}' and all its templates?", parent=self): return
        try:
            profile_path = Path(self.parent_app.profiles_root_path.get()) / profile_to_delete
            shutil.rmtree(profile_path)
            self.parent_app._delete_profile_config(profile_to_delete)
            self.parent_app._update_profile_list(); self._populate_listbox()
        except Exception as e: messagebox.showerror("Error", f"Could not delete profile: {e}", parent=self)

    def _set_active_profile(self, event=None):
        selected_indices = self.profile_listbox.curselection()
        if not selected_indices: return
        selected_profile = self.profile_listbox.get(selected_indices[0])
        self.parent_app.active_profile.set(selected_profile)
        self.parent_app._on_profile_change(); self.destroy()


class NexusAutoDL:
    APP_VERSION = "v0.6.0"; CONFIG_FILE = "config.json"; CLICK_TOLERANCE = 3
    MIN_CAPTURE_SIZE = 10; TRANSPARENT_COLOR = "#010203"
    BG_COLOR = "#2E2E2E"; FG_COLOR = "#EAEAEA"; INPUT_BG_COLOR = "#3C3C3C"
    BUTTON_BG_COLOR = "#555555"; BUTTON_ACTIVE_BG_COLOR = "#6A6A6A"
    SECONDARY_FG_COLOR = "#888888"

    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title(f"Nexus AutoDL {self.APP_VERSION}")
        self.root.resizable(False, False); self.root.config(bg=self.BG_COLOR)
        self._is_running = False; self._after_id: Optional[str] = None
        self._last_active_profile = ""
        self.config = {}
        self.confidence = DoubleVar(); self.grayscale = BooleanVar()
        self.min_sleep_seconds = DoubleVar(); self.max_sleep_seconds = DoubleVar()
        self.always_on_top = BooleanVar()
        self.show_visual_feedback = BooleanVar(); self.feedback_color = StringVar()
        self.feedback_duration = IntVar()
        self.profiles_root_path = StringVar(); self.active_profile = StringVar()
        self.search_mode = StringVar()
        self.sequence_index = 0
        self.log_window: Optional[Toplevel] = None
        self.log_text_widget: Optional[Text] = None
        self.templates: Dict[str, Image.Image] = {}
        
        self._setup_ttk_style(); self._load_config(); self._setup_ui()
        self._update_profile_list(); self._update_always_on_top()
        self.keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self.keyboard_listener.start()
        self.root.protocol("WM_DELETE_WINDOW", self._terminate_app)

    def _setup_ttk_style(self):
        style = ttk.Style(); style.theme_use('clam')
        style.configure("TCombobox", fieldbackground=self.INPUT_BG_COLOR, background=self.BUTTON_BG_COLOR, foreground=self.FG_COLOR, arrowcolor=self.FG_COLOR, selectbackground=self.INPUT_BG_COLOR, selectforeground=self.FG_COLOR, bordercolor=self.BG_COLOR, lightcolor=self.BG_COLOR, darkcolor=self.BG_COLOR)
        style.map('TCombobox', fieldbackground=[('readonly', self.INPUT_BG_COLOR)], selectbackground=[('readonly', self.INPUT_BG_COLOR)], selectforeground=[('readonly', self.FG_COLOR)])
        style.configure("TRadiobutton", background=self.BG_COLOR, foreground=self.FG_COLOR, indicatorcolor=self.INPUT_BG_COLOR)
        style.map("TRadiobutton", background=[('active', self.BG_COLOR)], indicatorcolor=[('active', self.BUTTON_ACTIVE_BG_COLOR)], foreground=[('active', self.FG_COLOR)])

    def _setup_ui(self):
        main_frame = Frame(self.root, padx=10, pady=10, bg=self.BG_COLOR)
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.grid_columnconfigure(0, weight=1)
        
        label_style = {"bg": self.BG_COLOR, "fg": self.FG_COLOR}
        entry_style = {"bg": self.INPUT_BG_COLOR, "fg": self.FG_COLOR, "insertbackground": self.FG_COLOR, "bd": 1, "highlightthickness": 0}
        button_style = {"bg": self.BUTTON_BG_COLOR, "fg": self.FG_COLOR, "activebackground": self.BUTTON_ACTIVE_BG_COLOR, "activeforeground": self.FG_COLOR, "bd": 0, "padx": 10}
        check_style = {**label_style, "selectcolor": self.INPUT_BG_COLOR, "activebackground": self.BG_COLOR}
        labelframe_style = {"bg": self.BG_COLOR, "fg": self.FG_COLOR, "padx": 10, "pady": 10}

        self.profile_frame = LabelFrame(main_frame, text="Profile Settings", **labelframe_style)
        self.profile_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tuning_frame = LabelFrame(main_frame, text="Automation Tuning", **labelframe_style)
        tuning_frame.grid(row=1, column=0, sticky="ew", pady=10)
        display_frame = LabelFrame(main_frame, text="Display & Behavior", **labelframe_style)
        display_frame.grid(row=2, column=0, sticky="ew", pady=10)
        self.sequence_frame = LabelFrame(main_frame, text="Sequence Editor", **labelframe_style)
        action_frame = Frame(main_frame, bg=self.BG_COLOR)
        action_frame.grid(row=4, column=0, sticky="ew", pady=(15, 0))
        status_frame = Frame(main_frame, bg=self.BG_COLOR)
        status_frame.grid(row=5, column=0, sticky="ew", pady=(10,0))
        main_frame.grid_columnconfigure(0, weight=1)
        
        Label(self.profile_frame, text="Active Profile:", **label_style).grid(row=0, column=0, sticky="w")
        self.profile_combobox = ttk.Combobox(self.profile_frame, textvariable=self.active_profile, state="readonly", width=30)
        self.profile_combobox.grid(row=0, column=1, sticky="ew", padx=5)
        self.profile_combobox.bind("<<ComboboxSelected>>", self._on_profile_change)
        self.manage_profiles_button = Button(self.profile_frame, text="Manage...", command=self._open_profile_manager, **button_style); self.manage_profiles_button.grid(row=0, column=2)
        self.profile_frame.grid_columnconfigure(1, weight=1)

        self.sequence_listbox = Listbox(self.sequence_frame, bg=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=0, highlightthickness=0, selectbackground=self.BUTTON_ACTIVE_BG_COLOR, height=5, exportselection=False)
        self.sequence_listbox.pack(side="left", fill="x", expand=True)
        seq_button_frame = Frame(self.sequence_frame, bg=self.BG_COLOR); seq_button_frame.pack(side="left", padx=5)
        self.move_up_button = Button(seq_button_frame, text="▲", command=self._move_template_up, **button_style); self.move_up_button.pack(pady=2, fill="x")
        self.move_down_button = Button(seq_button_frame, text="▼", command=self._move_template_down, **button_style); self.move_down_button.pack(pady=2, fill="x")

        Label(tuning_frame, text="Confidence:", **label_style).grid(row=0, column=0, sticky="w")
        self.confidence_entry = Entry(tuning_frame, textvariable=self.confidence, **entry_style, width=10); self.confidence_entry.grid(row=0, column=1, padx=5)
        Label(tuning_frame, text="Search Mode:", **label_style).grid(row=0, column=2, sticky="w", padx=(15,0))
        radio_frame = Frame(tuning_frame, bg=self.BG_COLOR); radio_frame.grid(row=0, column=3, columnspan=3, sticky="w")
        self.priority_radio = ttk.Radiobutton(radio_frame, text="Priority", variable=self.search_mode, value="priority", command=self._toggle_sequence_editor, style="TRadiobutton"); self.priority_radio.pack(side="left", padx=(5, 20))
        self.sequence_radio = ttk.Radiobutton(radio_frame, text="Sequence", variable=self.search_mode, value="sequence", command=self._toggle_sequence_editor, style="TRadiobutton"); self.sequence_radio.pack(side="left")
        Label(tuning_frame, text="Min Sleep (s):", **label_style).grid(row=1, column=0, sticky="w", pady=(10,0))
        self.min_sleep_entry = Entry(tuning_frame, textvariable=self.min_sleep_seconds, **entry_style, width=10); self.min_sleep_entry.grid(row=1, column=1, padx=5, pady=(10,0))
        Label(tuning_frame, text="Max Sleep (s):", **label_style).grid(row=1, column=2, sticky="w", padx=(15, 0), pady=(10,0))
        self.max_sleep_entry = Entry(tuning_frame, textvariable=self.max_sleep_seconds, **entry_style, width=10); self.max_sleep_entry.grid(row=1, column=3, padx=5, pady=(10,0))
        self.grayscale_check = Checkbutton(tuning_frame, text="Grayscale Matching", variable=self.grayscale, **check_style); self.grayscale_check.grid(row=2, column=0, columnspan=2, sticky='w', pady=(10,0))
        
        self.always_on_top_check = Checkbutton(display_frame, text="Always on Top", variable=self.always_on_top, command=self._update_always_on_top, **check_style); self.always_on_top_check.grid(row=0, column=0, sticky='w')
        self.visual_feedback_check = Checkbutton(display_frame, text="Visual Feedback", variable=self.show_visual_feedback, command=self._toggle_feedback_options, **check_style); self.visual_feedback_check.grid(row=1, column=0, sticky='w', pady=(10,0))
        self.feedback_options_frame = Frame(display_frame, bg=self.BG_COLOR); self.feedback_options_frame.grid(row=2, column=0, columnspan=2, sticky='w', padx=(20, 0))
        Label(self.feedback_options_frame, text="Color:", **label_style).grid(row=0, column=0, sticky="w")
        self.color_swatch = Label(self.feedback_options_frame, text="    ", bg=self.feedback_color.get(), relief="sunken", bd=1); self.color_swatch.grid(row=0, column=1, padx=5); self.color_swatch.bind("<Button-1>", self._choose_color)
        self.color_entry = Entry(self.feedback_options_frame, textvariable=self.feedback_color, **entry_style, width=10, state="readonly", readonlybackground=self.INPUT_BG_COLOR); self.color_entry.grid(row=0, column=2)
        Label(self.feedback_options_frame, text="Duration (ms):", **label_style).grid(row=0, column=3, sticky="w", padx=(15,0))
        self.duration_entry = Entry(self.feedback_options_frame, textvariable=self.feedback_duration, **entry_style, width=10); self.duration_entry.grid(row=0, column=4, padx=5)

        self.create_button = Button(action_frame, text="Create Template", command=self._start_capture_mode, **button_style); self.create_button.pack(side="left", expand=True, ipady=8, padx=(0, 5))
        self.start_button = Button(action_frame, text="Start (F3)", command=self._start_handler, **button_style); self.start_button.pack(side="left", expand=True, ipady=8)
        Label(status_frame, text="F3: Start/Resume  |  F4: Pause", bg=self.BG_COLOR, fg=self.SECONDARY_FG_COLOR).pack(side="left")
        Label(status_frame, text=self.APP_VERSION, bg=self.BG_COLOR, fg=self.SECONDARY_FG_COLOR).pack(side="right")
        
        self._add_tooltips(); self._toggle_feedback_options(); self._toggle_sequence_editor()

    def _add_tooltips(self):
        Tooltip(self.profile_combobox, "Select the active profile for automation."); Tooltip(self.manage_profiles_button, "Open the Profile Manager to create, rename, or delete profiles.")
        Tooltip(self.confidence_entry, "The accuracy required for a match (0.0 to 1.0).\nLower values are less strict. Requires OpenCV."); Tooltip(self.min_sleep_entry, "The minimum time in seconds to wait between search cycles."); Tooltip(self.max_sleep_entry, "The maximum time in seconds to wait between search cycles.")
        Tooltip(self.priority_radio, "Checks for templates one by one, in alphabetical order.\nIt clicks the first match it finds and then rests."); Tooltip(self.sequence_radio, "Searches for templates one by one in the exact order\ndefined in the Sequence Editor.")
        Tooltip(self.grayscale_check, "Searches for templates in black and white.\nThis is often faster but can be less accurate for some images.")
        Tooltip(self.sequence_listbox, "Define the exact order templates should be searched in Sequence Mode."); Tooltip(self.move_up_button, "Move the selected template up in the sequence."); Tooltip(self.move_down_button, "Move the selected template down in the sequence.")
        Tooltip(self.always_on_top_check, "Keeps the application and log windows above all other windows."); Tooltip(self.visual_feedback_check, "Briefly shows a colored border around a matched template before clicking.")
        Tooltip(self.color_swatch, "Click to choose the color of the feedback border."); Tooltip(self.color_entry, "The currently selected color in hex format."); Tooltip(self.duration_entry, "How long the feedback border stays on screen, in milliseconds.")
        Tooltip(self.create_button, "Capture a new template by drawing a rectangle on your screen."); Tooltip(self.start_button, "Start or Resume the automation process (F3).")
    
    def _toggle_feedback_options(self):
        if self.show_visual_feedback.get(): self.feedback_options_frame.grid(row=2, column=0, columnspan=2, sticky='w', padx=(20, 0), pady=5)
        else: self.feedback_options_frame.grid_forget()
    def _toggle_sequence_editor(self):
        self._populate_sequence_listbox()
        if self.search_mode.get() == "sequence":
            self.sequence_frame.grid(row=3, column=0, sticky="ew", pady=10)
        else:
            self.sequence_frame.grid_forget()
    def _choose_color(self, event=None):
        _, color_hex = colorchooser.askcolor(parent=self.root, initialcolor=self.feedback_color.get())
        if color_hex: self.feedback_color.set(color_hex); self.color_swatch.config(bg=color_hex)
    def _show_feedback_box(self, box):
        feedback_window = Toplevel(self.root); feedback_window.overrideredirect(True)
        feedback_window.geometry(f'{box.width}x{box.height}+{box.left}+{box.top}')
        feedback_window.config(bg=self.TRANSPARENT_COLOR); feedback_window.wm_attributes("-transparentcolor", self.TRANSPARENT_COLOR); feedback_window.attributes("-topmost", True)
        border_frame = Frame(feedback_window, highlightbackground=self.feedback_color.get(), highlightthickness=3, bg=self.TRANSPARENT_COLOR)
        border_frame.pack(fill="both", expand=True); self.root.update_idletasks()
        return feedback_window
    def _start_capture_mode(self):
        if not self.active_profile.get(): messagebox.showwarning("No Profile Selected", "Please select or create a profile before adding a template."); return
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
        if width > self.MIN_CAPTURE_SIZE and height > self.MIN_CAPTURE_SIZE:
            try:
                region_tuple = (int(x1), int(y1), int(width), int(height))
                img = pyautogui.screenshot(region=region_tuple)
                profile_dir = Path(self.profiles_root_path.get()) / self.active_profile.get()
                profile_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = profile_dir / f"template_{timestamp}.png"
                img.save(save_path)
                self._populate_sequence_listbox()
                messagebox.showinfo("Success", f"Template saved to profile '{self.active_profile.get()}':\n{save_path}")
            except Exception as e: messagebox.showerror("Error", f"Failed to save template: {e}")
        self.root.deiconify()
    def _log(self, message: str, level: str = "INFO"):
        if not self.log_text_widget: return
        self.log_text_widget.config(state="normal")
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text_widget.insert("end", f"[{timestamp}][{level}] {message}\n"); self.log_text_widget.see("end")
        self.log_text_widget.config(state="disabled")
    def _load_config(self):
        try:
            with open(self.CONFIG_FILE, "r") as f: self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): self.config = {}
        self.profiles_root_path.set(self.config.get("profiles_root_path", "profiles"))
        self.active_profile.set(self.config.get("active_profile", ""))
        self.always_on_top.set(self.config.get("always_on_top", False))
        self.show_visual_feedback.set(self.config.get("show_visual_feedback", False))
        self.feedback_color.set(self.config.get("feedback_color", "#00FF00"))
        self.feedback_duration.set(self.config.get("feedback_duration", 400))
        self._load_profile_settings()
        self._last_active_profile = self.active_profile.get()
    def _save_config(self):
        self._save_current_profile_settings()
        self.config["profiles_root_path"] = self.profiles_root_path.get()
        self.config["active_profile"] = self.active_profile.get()
        self.config["always_on_top"] = self.always_on_top.get()
        self.config["show_visual_feedback"] = self.show_visual_feedback.get()
        self.config["feedback_color"] = self.feedback_color.get()
        self.config["feedback_duration"] = self.feedback_duration.get()
        with open(self.CONFIG_FILE, "w") as f: json.dump(self.config, f, indent=4)
    def _validate_inputs(self) -> bool:
        try:
            if not self.active_profile.get(): messagebox.showerror("Invalid Setup", "No active profile selected. Please select or create a profile."); return False
            return True
        except (ValueError, TypeError):
            messagebox.showerror("Invalid Input", "Please ensure all fields contain valid numbers."); return False
    def _on_press(self, key):
        if key == keyboard.Key.f3: self.root.after_idle(self._start_handler)
        elif key == keyboard.Key.f4: self.root.after_idle(self._pause_handler)
    def _select_profiles_root(self):
        path = filedialog.askdirectory(title="Select Profiles Root Directory")
        if path: self.profiles_root_path.set(path); self._update_profile_list()
    def get_profiles(self) -> list:
        root_path = Path(self.profiles_root_path.get())
        if not root_path.is_dir(): return []
        return [d.name for d in root_path.iterdir() if d.is_dir()]
    def _update_profile_list(self):
        profiles = sorted(self.get_profiles())
        self.profile_combobox['values'] = profiles
        saved_profile = self.active_profile.get()
        if saved_profile in profiles: self.profile_combobox.set(saved_profile)
        elif profiles: self.profile_combobox.set(profiles[0])
        else: self.profile_combobox.set("")
        self._on_profile_change()
    def _on_profile_change(self, event=None):
        if self._last_active_profile and self._last_active_profile != self.active_profile.get():
            self._save_current_profile_settings()
        self._load_profile_settings()
        self._populate_sequence_listbox()
        self._last_active_profile = self.active_profile.get()
    def _populate_sequence_listbox(self):
        self.sequence_listbox.delete(0, 'end')
        profile_name = self.active_profile.get()
        if not profile_name: return
        profile_path = Path(self.profiles_root_path.get()) / profile_name
        if not profile_path.is_dir(): return
        actual_files = {p.name for p in profile_path.iterdir() if p.is_file()}
        profile_settings = self.config.get("profile_settings", {}).get(profile_name, {})
        saved_sequence = profile_settings.get("sequence", [])
        final_sequence = [f for f in saved_sequence if f in actual_files]
        new_files = sorted([f for f in actual_files if f not in final_sequence])
        final_sequence.extend(new_files)
        for item in final_sequence: self.sequence_listbox.insert('end', item)
    def _move_template_up(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices: return
        idx = selected_indices[0]
        if idx > 0:
            item = self.sequence_listbox.get(idx); self.sequence_listbox.delete(idx); self.sequence_listbox.insert(idx - 1, item)
            self.sequence_listbox.selection_set(idx - 1); self.sequence_listbox.activate(idx - 1)
    def _move_template_down(self):
        selected_indices = self.sequence_listbox.curselection()
        if not selected_indices: return
        idx = selected_indices[0]
        if idx < self.sequence_listbox.size() - 1:
            item = self.sequence_listbox.get(idx); self.sequence_listbox.delete(idx); self.sequence_listbox.insert(idx + 1, item)
            self.sequence_listbox.selection_set(idx + 1); self.sequence_listbox.activate(idx + 1)
    def _create_new_profile(self, parent_window=None):
        parent = parent_window if parent_window else self.root
        new_profile_name = simpledialog.askstring("New Profile", "Enter a name for the new profile:", parent=parent)
        if not new_profile_name or not new_profile_name.strip(): return
        root_path = Path(self.profiles_root_path.get())
        root_path.mkdir(exist_ok=True)
        new_profile_path = root_path / new_profile_name
        if new_profile_path.exists(): messagebox.showwarning("Profile Exists", f"A profile named '{new_profile_name}' already exists.", parent=parent); return
        try:
            new_profile_path.mkdir(parents=True, exist_ok=True)
            self._update_profile_list(); self.active_profile.set(new_profile_name)
            self._populate_sequence_listbox()
            messagebox.showinfo("Success", f"Profile '{new_profile_name}' created successfully.", parent=parent)
        except Exception as e: messagebox.showerror("Error", f"Could not create profile directory: {e}", parent=parent)
    def _open_profile_manager(self):
        ProfileManagerWindow(self)
    def _update_always_on_top(self):
        is_on_top = self.always_on_top.get()
        self.root.attributes("-topmost", is_on_top)
        if self.log_window and self.log_window.winfo_exists(): self.log_window.attributes("-topmost", is_on_top)
    def _start_handler(self):
        if self._is_running: return
        if not self._validate_inputs(): return
        self._is_running = True; self.start_button.config(state="disabled", text="Running...")
        self.sequence_index = 0
        if self.log_window is None: self._show_log_window()
        self._load_templates()
        if self.log_window: self.root.withdraw()
        self._match_loop()
    def _pause_handler(self):
        if not self._is_running: return
        self._is_running = False
        if self._after_id: self.root.after_cancel(self._after_id)
        self.start_button.config(state="normal", text="Resume (F3)")
        self.root.deiconify(); self._log("Process paused. Press F3 to resume.", "WARN")
    def _load_templates(self):
        self.templates.clear()
        profile_path = Path(self.profiles_root_path.get()) / self.active_profile.get()
        if not profile_path.is_dir(): return
        all_template_files = sorted([p for p in profile_path.iterdir() if p.is_file()], key=_human_sort)
        for path in all_template_files:
            try:
                img = open_image(path); self.templates[path.name] = img.copy(); img.close()
            except (IsADirectoryError, UnidentifiedImageError): pass
    def _match_loop(self):
        if not self._is_running: return
        self._perform_match()
        sleep_interval = random.uniform(self.min_sleep_seconds.get(), self.max_sleep_seconds.get())
        self._log(f"Waiting for {sleep_interval:.2f} seconds.")
        self._after_id = self.root.after(int(sleep_interval * 1000), self._match_loop)
    def _perform_click_action(self, box, path_name):
        center_x, center_y = pyautogui.center(box)
        click_x = center_x + random.randint(-self.CLICK_TOLERANCE, self.CLICK_TOLERANCE)
        click_y = center_y + random.randint(-self.CLICK_TOLERANCE, self.CLICK_TOLERANCE)
        original_pos = pyautogui.position(); pyautogui.click(click_x, click_y); pyautogui.moveTo(original_pos)
        self._log(f"Clicked {path_name} at ({click_x}, {click_y})", "INFO")
    def _perform_match(self):
        if not self.templates:
            self._log(f"No templates loaded for profile '{self.active_profile.get()}'. Pausing.", "WARN"); self._pause_handler(); return
        screenshot = pyautogui.screenshot()
        if self.search_mode.get() == "sequence": self._perform_match_sequence(screenshot)
        else: self._perform_match_priority(screenshot)
    def _perform_match_priority(self, screenshot):
        search_kwargs: Dict[str, Any] = {"grayscale": self.grayscale.get()}
        if has_cv2: search_kwargs["confidence"] = self.confidence.get()
        sorted_template_names = sorted(self.templates.keys(), key=str.lower)
        for name in sorted_template_names:
            image = self.templates.get(name)
            if not image: continue
            self._log(f"Attempting to find {name}.")
            try:
                box = pyautogui.locate(image, screenshot, **search_kwargs)
                if box: self._handle_found_match(box, name); return
            except pyautogui.PyAutoGUIException as e: self._log(f"Search error for {name}: {e}", "WARN")
    def _perform_match_sequence(self, screenshot):
        sequence = list(self.sequence_listbox.get(0, 'end'))
        if not sequence: self._log("Sequence is empty. Pausing.", "WARN"); self._pause_handler(); return
        self.sequence_index %= len(sequence)
        target_name = sequence[self.sequence_index]
        image_to_find = self.templates.get(target_name)
        if not image_to_find: self._log(f"Template '{target_name}' for sequence step not found in memory. Pausing.", "FATAL"); self._pause_handler(); return
        self._log(f"Searching for sequence step {self.sequence_index + 1}/{len(sequence)}: '{target_name}'.")
        search_kwargs: Dict[str, Any] = {"grayscale": self.grayscale.get()}
        if has_cv2: search_kwargs["confidence"] = self.confidence.get()
        try:
            box = pyautogui.locate(image_to_find, screenshot, **search_kwargs)
            if box:
                self.sequence_index = (self.sequence_index + 1) % len(sequence)
                self._handle_found_match(box, target_name)
        except pyautogui.PyAutoGUIException as e: self._log(f"Search error for {target_name}: {e}", "WARN")
    def _handle_found_match(self, box, path_name):
        if self.show_visual_feedback.get():
            feedback_box = self._show_feedback_box(box)
            self.root.after(self.feedback_duration.get(), lambda: (
                feedback_box.destroy(), self._perform_click_action(box, path_name)
            ))
        else:
            self._perform_click_action(box, path_name)
    def _show_log_window(self):
        self.root.withdraw()
        self.log_window = Toplevel(self.root)
        self.log_window.title("Log Console"); self.log_window.protocol("WM_DELETE_WINDOW", self._terminate_app); self.log_window.config(bg=self.BG_COLOR)
        self._update_always_on_top()
        main_log_frame = Frame(self.log_window, bg=self.BG_COLOR); main_log_frame.pack(padx=10, pady=10, fill="both", expand=True)
        help_label = Label(main_log_frame, text="F3: Resume  |  F4: Pause & Show Settings", bg=self.BG_COLOR, fg=self.SECONDARY_FG_COLOR)
        help_label.pack(pady=(0, 5))
        text_frame = Frame(main_log_frame, bg=self.BG_COLOR); text_frame.pack(fill="both", expand=True)
        self.log_text_widget = Text(text_frame, height=20, width=100, wrap="word", bg=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=0, highlightthickness=0); self.log_text_widget.pack(side="left", fill="both", expand=True)
        scrollbar = Scrollbar(text_frame, command=self.log_text_widget.yview, bg=self.BG_COLOR, troughcolor=self.INPUT_BG_COLOR, bd=0, activebackground=self.BUTTON_ACTIVE_BG_COLOR); scrollbar.pack(side="right", fill="y")
        self.log_text_widget.config(yscrollcommand=scrollbar.set, state="disabled")
        self._log(f"Activating profile: '{self.active_profile.get()}' with search mode: '{self.search_mode.get()}'")
        self._log("Process started. Starting search loop...")
        if not has_cv2:
            self._log("Note: Confidence setting is ignored because OpenCV is not installed. Run: pip install opencv-python", "WARN")
    def _terminate_app(self):
        self._save_config()
        self._is_running = False
        if self._after_id: self.root.after_cancel(self._after_id)
        if self.keyboard_listener.is_alive(): self.keyboard_listener.stop()
        self.root.destroy()
    def _load_profile_settings(self):
        """Loads the settings for the currently active profile."""
        profile_name = self.active_profile.get()
        if not profile_name: # Handle case with no active profile
            # Get default settings
            profile_settings = {}
        else:
            # Get the settings for this specific profile, or an empty dict if none exist
            all_profile_settings = self.config.get("profile_settings", {})
            profile_settings = all_profile_settings.get(profile_name, {})
        
        # Set UI variables, falling back to global defaults if a setting is missing
        self.confidence.set(profile_settings.get("confidence", 0.8))
        self.grayscale.set(profile_settings.get("grayscale", True))
        self.min_sleep_seconds.set(profile_settings.get("min_sleep", 1.0))
        self.max_sleep_seconds.set(profile_settings.get("max_sleep", 5.0))
        self.search_mode.set(profile_settings.get("search_mode", "priority"))

    def _save_current_profile_settings(self):
        """Saves the current UI settings into the config object for the active profile."""
        profile_name = self._last_active_profile
        if not profile_name: return # Nothing to save if no profile was active
        
        if "profile_settings" not in self.config:
            self.config["profile_settings"] = {}
        
        self.config["profile_settings"][profile_name] = {
            "confidence": self.confidence.get(),
            "grayscale": self.grayscale.get(),
            "min_sleep": self.min_sleep_seconds.get(),
            "max_sleep": self.max_sleep_seconds.get(),
            "search_mode": self.search_mode.get(),
            "sequence": list(self.sequence_listbox.get(0, 'end'))
        }

    def _rename_profile_config(self, old_name, new_name):
        """Updates the profile name in the configuration data."""
        if "profile_settings" in self.config and old_name in self.config["profile_settings"]:
            self.config["profile_settings"][new_name] = self.config["profile_settings"].pop(old_name)
    
    def _delete_profile_config(self, profile_name):
        """Removes a profile's settings from the configuration data."""
        if "profile_settings" in self.config:
            self.config["profile_settings"].pop(profile_name, None)

if __name__ == "__main__":
    main_root = Tk()
    app = NexusAutoDL(main_root)
    try:
        main_root.mainloop()
    except KeyboardInterrupt:
        app._terminate_app()
