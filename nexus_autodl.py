"""
Nexus AutoDL - Automation Script

v0.6.2
"""

import json
import os
import random
import re
import shutil
from datetime import datetime
from pathlib import Path
from tkinter import (BooleanVar, Button, Checkbutton, DoubleVar, Entry, Frame,
                     Label, Listbox, Scrollbar, StringVar, Text, Tk, Toplevel,
                     filedialog, Canvas, LabelFrame, colorchooser, IntVar)
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Dict, Optional, List

# --- Dependency Check ---
try:
    from pynput import keyboard
    import pyautogui
    from PIL import UnidentifiedImageError, Image, ImageTk
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

class TemplateCache:
    
    def __init__(self, max_cache_size: int = 50):
        self._cache: Dict[str, Image.Image] = {}
        self._timestamps: Dict[str, float] = {}
        self._access_order: List[str] = []
        self._max_size = max_cache_size
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_template(self, template_path: Path) -> Optional[Image.Image]:
        path_str = str(template_path)
        
        if not template_path.exists():
            return None
            
        try:
            file_mtime = template_path.stat().st_mtime
            
            if (path_str in self._cache and 
                path_str in self._timestamps and 
                self._timestamps[path_str] >= file_mtime):
                
                self._update_access_order(path_str)
                self._cache_hits += 1
                return self._cache[path_str]
            
            img = open_image(template_path)
            template_copy = img.copy()
            img.close()
            
            self._store_template(path_str, template_copy, file_mtime)
            self._cache_misses += 1
            
            return template_copy
            
        except Exception:
            return None
    
    def _store_template(self, path_str: str, template: Image.Image, mtime: float):
        if path_str in self._cache:
            self._remove_from_cache(path_str)
        
        while len(self._cache) >= self._max_size:
            if not self._access_order:
                break
            oldest_path = self._access_order[0]
            self._remove_from_cache(oldest_path)
        
        self._cache[path_str] = template
        self._timestamps[path_str] = mtime
        self._access_order.append(path_str)
    
    def _update_access_order(self, path_str: str):
        if path_str in self._access_order:
            self._access_order.remove(path_str)
        self._access_order.append(path_str)
    
    def _remove_from_cache(self, path_str: str):
        self._cache.pop(path_str, None)
        self._timestamps.pop(path_str, None)
        if path_str in self._access_order:
            self._access_order.remove(path_str)
    
    def invalidate_template(self, template_path: Path):
        path_str = str(template_path)
        self._remove_from_cache(path_str)
    
    def clear_cache(self):
        self._cache.clear()
        self._timestamps.clear()
        self._access_order.clear()
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': hit_rate,
            'cached_templates': list(self._cache.keys())
        }

class TemplatePreviewWindow(Toplevel):
    
    def __init__(self, parent, template_path: Path):
        super().__init__(parent)
        self.parent = parent
        self.template_path = template_path
        
        self.title(f"Template Preview - {template_path.name}")
        self.config(bg="#2E2E2E")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        try:
            self._setup_ui()
            self._center_window()
        except Exception:
            self.destroy()
            messagebox.showerror("Preview Error", f"Unable to load template preview for '{template_path.name}'", parent=parent)
    
    def _setup_ui(self):
        try:
            img = open_image(self.template_path)
            original_size = (img.width, img.height)
            
            max_size = 400
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            self.photo = ImageTk.PhotoImage(img)
            
            main_frame = Frame(self, bg="#2E2E2E", padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            
            info_frame = Frame(main_frame, bg="#2E2E2E")
            info_frame.pack(fill="x", pady=(0, 15))
            
            Label(info_frame, text=f"File: {self.template_path.name}", 
                  bg="#2E2E2E", fg="#EAEAEA", font=("Segoe UI", 10, "bold")).pack(anchor="w")
            Label(info_frame, text=f"Original Size: {original_size[0]}x{original_size[1]} pixels", 
                  bg="#2E2E2E", fg="#888888", font=("Segoe UI", 9)).pack(anchor="w")
            if img.size != original_size:
                Label(info_frame, text=f"Preview Size: {img.width}x{img.height} pixels (scaled)", 
                      bg="#2E2E2E", fg="#888888", font=("Segoe UI", 9)).pack(anchor="w")
            
            image_frame = Frame(main_frame, bg="#1A1A1A", relief="solid", bd=1)
            image_frame.pack(pady=15)
            image_label = Label(image_frame, image=self.photo, bg="#1A1A1A")
            image_label.pack(padx=8, pady=8)
            
            close_btn = Button(main_frame, text="Close", command=self.destroy,
                              bg="#555555", fg="#EAEAEA", activebackground="#6A6A6A", 
                              activeforeground="#FFFFFF", bd=0, padx=30, pady=8, 
                              font=("Segoe UI", 9), cursor="hand2")
            close_btn.pack(pady=(20, 0))
            
        except Exception as e:
            error_frame = Frame(self, bg="#2E2E2E", padx=40, pady=40)
            error_frame.pack(fill="both", expand=True)
            
            Label(error_frame, text="⚠", bg="#2E2E2E", fg="#FF6B6B", 
                  font=("Segoe UI", 24)).pack(pady=(0, 10))
            Label(error_frame, text="Unable to load image preview", 
                  bg="#2E2E2E", fg="#FF6B6B", font=("Segoe UI", 11, "bold")).pack(pady=(0, 5))
            Label(error_frame, text=f"Error: {str(e)}", 
                  bg="#2E2E2E", fg="#CCCCCC", font=("Segoe UI", 9)).pack(pady=(0, 20))
            
            close_btn = Button(error_frame, text="Close", command=self.destroy,
                              bg="#555555", fg="#EAEAEA", activebackground="#6A6A6A",
                              activeforeground="#FFFFFF", bd=0, padx=30, pady=8, 
                              font=("Segoe UI", 9), cursor="hand2")
            close_btn.pack()
    
    def _center_window(self):
        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        my_width = self.winfo_width()
        my_height = self.winfo_height()
        
        pos_x = parent_x + (parent_width // 2) - (my_width // 2)
        pos_y = parent_y + (parent_height // 2) - (my_height // 2)
        
        self.geometry(f"+{pos_x}+{pos_y}")

class Tooltip:
    
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
        label = Label(self.tooltip_window, text=self.text, justify='left', 
                     background="#1E1E1E", foreground="#EAEAEA", relief='solid', 
                     borderwidth=1, wraplength=300, padx=8, pady=5, font=("Segoe UI", 9))
        label.pack(ipadx=1)

    def hide_tooltip(self):
        if self.tooltip_window: self.tooltip_window.destroy(); self.tooltip_window = None

class ProfileManagerWindow(Toplevel):
    
    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.parent_app = parent_app
        self.transient(parent_app.root)
        self.title("Profile & Template Manager")
        self.config(bg=parent_app.BG_COLOR)
        self.resizable(True, True)
        self.grab_set()
        self._setup_ui()
        self._populate_profile_list()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        parent = self.parent_app.root
        parent_x, parent_y = parent.winfo_x(), parent.winfo_y()
        parent_width, parent_height = parent.winfo_width(), parent.winfo_height()
        my_width, my_height = 650, 500
        self.geometry(f"{my_width}x{my_height}")
        pos_x = (parent_width // 2) - (my_width // 2) + parent_x
        pos_y = (parent_height // 2) - (my_height // 2) + parent_y
        self.geometry(f"{my_width}x{my_height}+{pos_x}+{pos_y}")

    def _setup_ui(self):
        main_frame = Frame(self, bg=self.parent_app.BG_COLOR)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        header_frame = Frame(main_frame, bg=self.parent_app.BG_COLOR)
        header_frame.pack(fill="x", pady=(0, 15))
        
        title_label = Label(header_frame, text="Profile & Template Manager", 
                           bg=self.parent_app.BG_COLOR, fg=self.parent_app.FG_COLOR, 
                           font=("Segoe UI", 13, "bold"))
        title_label.pack(side="left")
        
        dir_frame = Frame(main_frame, bg=self.parent_app.BG_COLOR)
        dir_frame.pack(fill="x", pady=(0, 15))
        
        Label(dir_frame, text="Profiles Directory:", bg=self.parent_app.BG_COLOR, 
              fg=self.parent_app.FG_COLOR, font=("Segoe UI", 10)).pack(side="left")
        
        path_entry = Entry(dir_frame, textvariable=self.parent_app.profiles_root_path, 
                          state="readonly", readonlybackground=self.parent_app.INPUT_BG_COLOR, 
                          fg=self.parent_app.FG_COLOR, bd=1, font=("Segoe UI", 9))
        path_entry.pack(side="left", fill="x", expand=True, padx=(10, 10))
        
        browse_btn = Button(dir_frame, text="Browse...", command=self._select_profiles_root, 
                           bg=self.parent_app.BUTTON_BG_COLOR, fg=self.parent_app.FG_COLOR, 
                           activebackground=self.parent_app.BUTTON_ACTIVE_BG_COLOR,
                           activeforeground="#FFFFFF", bd=0, padx=15, pady=6, 
                           font=("Segoe UI", 9), cursor="hand2")
        browse_btn.pack(side="right")

        content_frame = Frame(main_frame, bg=self.parent_app.BG_COLOR)
        content_frame.pack(fill="both", expand=True)
        
        left_panel = LabelFrame(content_frame, text="Profiles", bg=self.parent_app.BG_COLOR, 
                               fg=self.parent_app.FG_COLOR, padx=10, pady=10, 
                               font=("Segoe UI", 10, "bold"))
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        profile_list_frame = Frame(left_panel, bg=self.parent_app.BG_COLOR)
        profile_list_frame.pack(fill="both", expand=True)
        
        self.profile_listbox = Listbox(profile_list_frame, bg=self.parent_app.INPUT_BG_COLOR, 
                                      fg=self.parent_app.FG_COLOR, bd=0, highlightthickness=0, 
                                      selectbackground=self.parent_app.BUTTON_ACTIVE_BG_COLOR, 
                                      exportselection=False, font=("Segoe UI", 9))
        self.profile_listbox.pack(side="left", fill="both", expand=True)
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)
        self.profile_listbox.bind("<Double-Button-1>", self._set_active_profile)
        
        profile_scrollbar = Scrollbar(profile_list_frame, command=self.profile_listbox.yview)
        profile_scrollbar.pack(side="right", fill="y")
        self.profile_listbox.config(yscrollcommand=profile_scrollbar.set)

        profile_buttons_frame = Frame(left_panel, bg=self.parent_app.BG_COLOR)
        profile_buttons_frame.pack(fill="x", pady=(10, 0))
        
        button_style = {
            "bg": self.parent_app.BUTTON_BG_COLOR, 
            "fg": self.parent_app.FG_COLOR, 
            "activebackground": self.parent_app.BUTTON_ACTIVE_BG_COLOR, 
            "activeforeground": "#FFFFFF", 
            "bd": 0, 
            "padx": 12, 
            "pady": 5, 
            "font": ("Segoe UI", 9), 
            "cursor": "hand2"
        }
        
        new_btn = Button(profile_buttons_frame, text="New", command=self._create_profile, **button_style)
        new_btn.pack(side="left")
        
        rename_btn = Button(profile_buttons_frame, text="Rename", command=self._rename_profile, **button_style)
        rename_btn.pack(side="left", padx=(6,0))
        
        delete_btn = Button(profile_buttons_frame, text="Delete", command=self._delete_profile, **button_style)
        delete_btn.pack(side="left", padx=(6,0))
        
        set_active_btn = Button(profile_buttons_frame, text="Set Active", 
                               command=self._set_active_profile, **button_style)
        set_active_btn.pack(side="right")

        right_panel = LabelFrame(content_frame, text="Templates", bg=self.parent_app.BG_COLOR, 
                                fg=self.parent_app.FG_COLOR, padx=10, pady=10, 
                                font=("Segoe UI", 10, "bold"))
        right_panel.pack(side="right", fill="both", expand=True, padx=(8, 0))
        
        template_list_frame = Frame(right_panel, bg=self.parent_app.BG_COLOR)
        template_list_frame.pack(fill="both", expand=True)
        
        self.template_listbox = Listbox(template_list_frame, bg=self.parent_app.INPUT_BG_COLOR, 
                                       fg=self.parent_app.FG_COLOR, bd=0, highlightthickness=0, 
                                       selectbackground=self.parent_app.BUTTON_ACTIVE_BG_COLOR, 
                                       exportselection=False, font=("Segoe UI", 9))
        self.template_listbox.pack(side="left", fill="both", expand=True)
        self.template_listbox.bind("<Double-Button-1>", self._preview_template)
        
        template_scrollbar = Scrollbar(template_list_frame, command=self.template_listbox.yview)
        template_scrollbar.pack(side="right", fill="y")
        self.template_listbox.config(yscrollcommand=template_scrollbar.set)

        template_buttons_frame = Frame(right_panel, bg=self.parent_app.BG_COLOR)
        template_buttons_frame.pack(fill="x", pady=(10, 0))
        
        preview_btn = Button(template_buttons_frame, text="Preview", 
                           command=self._preview_template, **button_style)
        preview_btn.pack(side="left")
        
        delete_template_btn = Button(template_buttons_frame, text="Delete", 
                                   command=self._delete_template, **button_style)
        delete_template_btn.pack(side="left", padx=(6,0))

    def _populate_profile_list(self):
        self.profile_listbox.delete(0, 'end')
        try:
            profiles = sorted(self.parent_app.get_profiles())
            if not profiles:
                self.profile_listbox.insert('end', "(No profiles found)")
                return
                
            for i, profile in enumerate(profiles):
                display_text = f"● {profile}" if profile == self.parent_app.active_profile.get() else f"  {profile}"
                self.profile_listbox.insert('end', display_text)
                if profile == self.parent_app.active_profile.get():
                    self.profile_listbox.selection_set(i)
                    self.profile_listbox.see(i)
                    self._populate_template_list(profile)
        except Exception as e:
            self.profile_listbox.insert('end', f"Error loading profiles: {str(e)}")

    def _populate_template_list(self, profile_name: str):
        self.template_listbox.delete(0, 'end')
        if not profile_name or profile_name.startswith("(") or profile_name.startswith("Error"):
            return
            
        try:
            profile_path = Path(self.parent_app.profiles_root_path.get()) / profile_name
            if not profile_path.is_dir():
                self.template_listbox.insert('end', "(Profile directory not found)")
                return
                
            template_files = sorted([f for f in profile_path.iterdir() 
                                   if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp']], 
                                   key=_human_sort)
            
            if not template_files:
                self.template_listbox.insert('end', "(No templates found)")
                return
                
            for template_file in template_files:
                self.template_listbox.insert('end', template_file.name)
        except Exception as e:
            self.template_listbox.insert('end', f"Error loading templates: {str(e)}")

    def _on_profile_select(self, event=None):
        selection = self.profile_listbox.curselection()
        if not selection:
            self.template_listbox.delete(0, 'end')
            return
            
        selected_text = self.profile_listbox.get(selection[0])
        if selected_text.startswith("(") or selected_text.startswith("Error"):
            self.template_listbox.delete(0, 'end')
            return
            
        profile_name = selected_text.replace("● ", "").replace("  ", "")
        self._populate_template_list(profile_name)

    def _get_selected_profile(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            return None
        selected_text = self.profile_listbox.get(selection[0])
        if selected_text.startswith("(") or selected_text.startswith("Error"):
            return None
        return selected_text.replace("● ", "").replace("  ", "")

    def _select_profiles_root(self):
        try:
            path = filedialog.askdirectory(title="Select Profiles Root Directory", parent=self)
            if path:
                self.parent_app.profiles_root_path.set(path)
                self.parent_app._update_profile_list()
                self._populate_profile_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not change profiles directory: {e}", parent=self)

    def _create_profile(self):
        try:
            self.parent_app._create_new_profile(parent_window=self)
            self._populate_profile_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not create profile: {e}", parent=self)

    def _rename_profile(self):
        profile_name = self._get_selected_profile()
        if not profile_name:
            messagebox.showwarning("No Selection", "Please select a profile to rename.", parent=self)
            return
            
        try:
            new_name = simpledialog.askstring("Rename Profile", f"Enter a new name for '{profile_name}':", parent=self)
            if not new_name or not new_name.strip() or new_name == profile_name:
                return
            
            if any(char in new_name for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
                messagebox.showerror("Invalid Name", "Profile name contains invalid characters.", parent=self)
                return
            
            root_path = Path(self.parent_app.profiles_root_path.get())
            old_path, new_path = root_path / profile_name, root_path / new_name
            if new_path.exists():
                messagebox.showerror("Error", f"A profile named '{new_name}' already exists.", parent=self)
                return
            
            old_path.rename(new_path)
            self.parent_app._rename_profile_config(profile_name, new_name)
            if self.parent_app.active_profile.get() == profile_name:
                self.parent_app.active_profile.set(new_name)
            self.parent_app._update_profile_list()
            self._populate_profile_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not rename profile: {e}", parent=self)

    def _delete_profile(self):
        profile_name = self._get_selected_profile()
        if not profile_name:
            messagebox.showwarning("No Selection", "Please select a profile to delete.", parent=self)
            return
        
        if not messagebox.askyesno("Confirm Deletion", 
                                 f"Are you sure you want to permanently delete the profile '{profile_name}' and all its templates?\n\nThis action cannot be undone.", 
                                 parent=self):
            return
        
        try:
            profile_path = Path(self.parent_app.profiles_root_path.get()) / profile_name
            if profile_path.exists():
                shutil.rmtree(profile_path)
            self.parent_app._delete_profile_config(profile_name)
            if self.parent_app.active_profile.get() == profile_name:
                self.parent_app.active_profile.set("")
            self.parent_app._update_profile_list()
            self._populate_profile_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete profile: {e}", parent=self)

    def _set_active_profile(self, event=None):
        profile_name = self._get_selected_profile()
        if not profile_name:
            messagebox.showwarning("No Selection", "Please select a profile to set as active.", parent=self)
            return
        
        try:
            self.parent_app.active_profile.set(profile_name)
            self.parent_app._on_profile_change()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not set active profile: {e}", parent=self)

    def _preview_template(self, event=None):
        template_selection = self.template_listbox.curselection()
        if not template_selection:
            messagebox.showwarning("No Selection", "Please select a template to preview.", parent=self)
            return
            
        template_name = self.template_listbox.get(template_selection[0])
        if template_name.startswith("(") or template_name.startswith("Error"):
            return
            
        profile_name = self._get_selected_profile()
        if not profile_name:
            return
            
        try:
            template_path = Path(self.parent_app.profiles_root_path.get()) / profile_name / template_name
            
            if not template_path.exists():
                messagebox.showerror("Error", f"Template file '{template_name}' not found.", parent=self)
                return
                
            TemplatePreviewWindow(self, template_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not preview template: {e}", parent=self)

    def _delete_template(self):
        template_selection = self.template_listbox.curselection()
        if not template_selection:
            messagebox.showwarning("No Selection", "Please select a template to delete.", parent=self)
            return
            
        template_name = self.template_listbox.get(template_selection[0])
        if template_name.startswith("(") or template_name.startswith("Error"):
            return
            
        profile_name = self._get_selected_profile()
        if not profile_name:
            return
        
        if not messagebox.askyesno("Confirm Deletion", 
                                 f"Are you sure you want to delete the template '{template_name}'?\n\nThis action cannot be undone.", 
                                 parent=self):
            return
        
        try:
            template_path = Path(self.parent_app.profiles_root_path.get()) / profile_name / template_name
            if template_path.exists():
                template_path.unlink()
                
                self.parent_app.template_cache.invalidate_template(template_path)
                self._populate_template_list(profile_name)
                self.parent_app._populate_sequence_listbox()
                
                messagebox.showinfo("Success", f"Template '{template_name}' deleted successfully.", parent=self)
            else:
                messagebox.showerror("Error", f"Template file '{template_name}' not found.", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Could not delete template: {e}", parent=self)

class NexusAutoDL:
    APP_VERSION = "v0.6.2"; CONFIG_FILE = "config.json"; CLICK_TOLERANCE = 3
    MIN_CAPTURE_SIZE = 10; TRANSPARENT_COLOR = "#010203"
    BG_COLOR = "#2E2E2E"; FG_COLOR = "#EAEAEA"; INPUT_BG_COLOR = "#3C3C3C"
    BUTTON_BG_COLOR = "#555555"; BUTTON_ACTIVE_BG_COLOR = "#6A6A6A"
    SECONDARY_FG_COLOR = "#888888"
    CACHE_SIZE = 50

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
        
        self.template_cache = TemplateCache(max_cache_size=self.CACHE_SIZE)
        self.templates: Dict[str, Image.Image] = {}
        
        self._setup_ttk_style(); self._load_config(); self._setup_ui()
        self._update_profile_list(); self._update_always_on_top()
        
        self.keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self.keyboard_listener.start()
        self.root.protocol("WM_DELETE_WINDOW", self._terminate_app)

    def _setup_ttk_style(self):
        style = ttk.Style(); style.theme_use('clam')
        style.configure("TCombobox", fieldbackground=self.INPUT_BG_COLOR, background=self.BUTTON_BG_COLOR, 
                       foreground=self.FG_COLOR, arrowcolor=self.FG_COLOR, selectbackground=self.INPUT_BG_COLOR, 
                       selectforeground=self.FG_COLOR, bordercolor=self.BG_COLOR, lightcolor=self.BG_COLOR, darkcolor=self.BG_COLOR)
        style.map('TCombobox', fieldbackground=[('readonly', self.INPUT_BG_COLOR)], 
                 selectbackground=[('readonly', self.INPUT_BG_COLOR)], selectforeground=[('readonly', self.FG_COLOR)])
        style.configure("TRadiobutton", background=self.BG_COLOR, foreground=self.FG_COLOR, indicatorcolor=self.INPUT_BG_COLOR)
        style.map("TRadiobutton", background=[('active', self.BG_COLOR)], 
                 indicatorcolor=[('active', self.BUTTON_ACTIVE_BG_COLOR)], foreground=[('active', self.FG_COLOR)])

    def _setup_ui(self):
        main_frame = Frame(self.root, padx=12, pady=12, bg=self.BG_COLOR)
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.grid_columnconfigure(0, weight=1)
        
        label_style = {"bg": self.BG_COLOR, "fg": self.FG_COLOR, "font": ("Segoe UI", 9)}
        entry_style = {"bg": self.INPUT_BG_COLOR, "fg": self.FG_COLOR, "insertbackground": self.FG_COLOR, "bd": 1, "highlightthickness": 0, "font": ("Segoe UI", 9)}
        button_style = {"bg": self.BUTTON_BG_COLOR, "fg": self.FG_COLOR, "activebackground": self.BUTTON_ACTIVE_BG_COLOR, "activeforeground": "#FFFFFF", "bd": 0, "padx": 12, "pady": 5, "font": ("Segoe UI", 9), "cursor": "hand2"}
        check_style = {**label_style, "selectcolor": self.INPUT_BG_COLOR, "activebackground": self.BG_COLOR}
        labelframe_style = {"bg": self.BG_COLOR, "fg": self.FG_COLOR, "padx": 12, "pady": 10, "font": ("Segoe UI", 10, "bold")}

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

        Label(self.profile_frame, text="Active Profile:", **label_style).grid(row=0, column=0, sticky="w", pady=3)
        self.profile_combobox = ttk.Combobox(self.profile_frame, textvariable=self.active_profile, state="readonly", width=28, font=("Segoe UI", 9))
        self.profile_combobox.grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=3)
        self.profile_combobox.bind("<<ComboboxSelected>>", self._on_profile_change)
        self.manage_profiles_button = Button(self.profile_frame, text="Manage...", command=self._open_profile_manager, **button_style)
        self.manage_profiles_button.grid(row=0, column=2, pady=3)
        self.profile_frame.grid_columnconfigure(1, weight=1)

        self.sequence_listbox = Listbox(self.sequence_frame, bg=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=0, highlightthickness=0, selectbackground=self.BUTTON_ACTIVE_BG_COLOR, height=4, exportselection=False, font=("Segoe UI", 9))
        self.sequence_listbox.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        seq_button_frame = Frame(self.sequence_frame, bg=self.BG_COLOR)
        seq_button_frame.pack(side="right")
        
        up_btn = Button(seq_button_frame, text="▲", command=self._move_template_up, 
                       bg=self.BUTTON_BG_COLOR, fg=self.FG_COLOR, 
                       activebackground=self.BUTTON_ACTIVE_BG_COLOR, activeforeground="#FFFFFF",
                       bd=0, padx=8, pady=3, font=("Segoe UI", 9), cursor="hand2")
        up_btn.pack(pady=(0, 3), fill="x")
        
        down_btn = Button(seq_button_frame, text="▼", command=self._move_template_down,
                         bg=self.BUTTON_BG_COLOR, fg=self.FG_COLOR, 
                         activebackground=self.BUTTON_ACTIVE_BG_COLOR, activeforeground="#FFFFFF",
                         bd=0, padx=8, pady=3, font=("Segoe UI", 9), cursor="hand2")
        down_btn.pack(fill="x")

        Label(tuning_frame, text="Confidence:", **label_style).grid(row=0, column=0, sticky="w", pady=3)
        self.confidence_entry = Entry(tuning_frame, textvariable=self.confidence, **entry_style, width=10)
        self.confidence_entry.grid(row=0, column=1, padx=(8, 0), pady=3)
        
        Label(tuning_frame, text="Search Mode:", **label_style).grid(row=0, column=2, sticky="w", padx=(20,0), pady=3)
        radio_frame = Frame(tuning_frame, bg=self.BG_COLOR)
        radio_frame.grid(row=0, column=3, columnspan=3, sticky="w", padx=(8, 0), pady=3)
        self.priority_radio = ttk.Radiobutton(radio_frame, text="Priority", variable=self.search_mode, value="priority", command=self._toggle_sequence_editor, style="TRadiobutton")
        self.priority_radio.pack(side="left", padx=(0, 20))
        self.sequence_radio = ttk.Radiobutton(radio_frame, text="Sequence", variable=self.search_mode, value="sequence", command=self._toggle_sequence_editor, style="TRadiobutton")
        self.sequence_radio.pack(side="left")

        Label(tuning_frame, text="Min Sleep (s):", **label_style).grid(row=1, column=0, sticky="w", pady=(10,3))
        self.min_sleep_entry = Entry(tuning_frame, textvariable=self.min_sleep_seconds, **entry_style, width=10)
        self.min_sleep_entry.grid(row=1, column=1, padx=(8, 0), pady=(10,3))
        Label(tuning_frame, text="Max Sleep (s):", **label_style).grid(row=1, column=2, sticky="w", padx=(20, 0), pady=(10,3))
        self.max_sleep_entry = Entry(tuning_frame, textvariable=self.max_sleep_seconds, **entry_style, width=10)
        self.max_sleep_entry.grid(row=1, column=3, padx=(8, 0), pady=(10,3))

        self.grayscale_check = Checkbutton(tuning_frame, text="Grayscale Matching", variable=self.grayscale, **check_style)
        self.grayscale_check.grid(row=2, column=0, columnspan=2, sticky='w', pady=(10,3))

        self.always_on_top_check = Checkbutton(display_frame, text="Always on Top", variable=self.always_on_top, command=self._update_always_on_top, **check_style)
        self.always_on_top_check.grid(row=0, column=0, sticky='w', pady=3)
        
        self.visual_feedback_check = Checkbutton(display_frame, text="Visual Feedback", variable=self.show_visual_feedback, command=self._toggle_feedback_options, **check_style)
        self.visual_feedback_check.grid(row=1, column=0, sticky='w', pady=(8,3))

        self.feedback_options_frame = Frame(display_frame, bg=self.BG_COLOR)
        self.feedback_options_frame.grid(row=2, column=0, columnspan=4, sticky='w', padx=(25, 0))
        
        Label(self.feedback_options_frame, text="Color:", **label_style).grid(row=0, column=0, sticky="w", pady=3)
        self.color_swatch = Label(self.feedback_options_frame, text="   ", bg=self.feedback_color.get(), relief="solid", bd=1, cursor="hand2")
        self.color_swatch.grid(row=0, column=1, padx=(8, 8), pady=3)
        self.color_swatch.bind("<Button-1>", self._choose_color)
        
        self.color_entry = Entry(self.feedback_options_frame, textvariable=self.feedback_color, **entry_style, width=8, state="readonly", readonlybackground=self.INPUT_BG_COLOR)
        self.color_entry.grid(row=0, column=2, pady=3)
        
        Label(self.feedback_options_frame, text="Duration (ms):", **label_style).grid(row=0, column=3, sticky="w", padx=(15,0), pady=3)
        self.duration_entry = Entry(self.feedback_options_frame, textvariable=self.feedback_duration, **entry_style, width=8)
        self.duration_entry.grid(row=0, column=4, padx=(8, 0), pady=3)

        self.create_button = Button(action_frame, text="Create Template", command=self._start_capture_mode, **button_style)
        self.create_button.pack(side="left", expand=True, padx=(0, 8))
        
        self.start_button = Button(action_frame, text="Start (F3)", command=self._start_handler, **button_style)
        self.start_button.pack(side="left", expand=True)

        Label(status_frame, text="F3: Start/Resume | F4: Pause", bg=self.BG_COLOR, fg=self.SECONDARY_FG_COLOR, font=("Segoe UI", 8)).pack(side="left")
        Label(status_frame, text=self.APP_VERSION, bg=self.BG_COLOR, fg=self.SECONDARY_FG_COLOR, font=("Segoe UI", 8)).pack(side="right")

        self._add_tooltips(); self._toggle_feedback_options(); self._toggle_sequence_editor()

    def _add_tooltips(self):
        Tooltip(self.profile_combobox, "Select the active profile for automation.")
        Tooltip(self.manage_profiles_button, "Open the Profile Manager to create, rename, or delete profiles and templates.")
        Tooltip(self.confidence_entry, "The accuracy required for a match (0.0 to 1.0).\nLower values are less strict. Requires OpenCV.")
        Tooltip(self.min_sleep_entry, "The minimum time in seconds to wait between search cycles.")
        Tooltip(self.max_sleep_entry, "The maximum time in seconds to wait between search cycles.")
        Tooltip(self.priority_radio, "Checks for templates one by one, in alphabetical order.\nIt clicks the first match it finds and then rests.")
        Tooltip(self.sequence_radio, "Searches for templates one by one in the exact order\ndefined in the Sequence Editor.")
        Tooltip(self.grayscale_check, "Searches for templates in black and white.\nThis is often faster but can be less accurate for some images.")
        Tooltip(self.sequence_listbox, "Define the exact order templates should be searched in Sequence Mode.")
        Tooltip(self.always_on_top_check, "Keeps the application and log windows above all other windows.")
        Tooltip(self.visual_feedback_check, "Briefly shows a colored border around a matched template before clicking.")
        Tooltip(self.color_swatch, "Click to choose the color of the feedback border.")
        Tooltip(self.color_entry, "The currently selected color in hex format.")
        Tooltip(self.duration_entry, "How long the feedback border stays on screen, in milliseconds.")
        Tooltip(self.create_button, "Capture a new template by drawing a rectangle on your screen. Press ESC to cancel.")
        Tooltip(self.start_button, "Start or Resume the automation process (F3).")

    def _toggle_feedback_options(self):
        if self.show_visual_feedback.get(): 
            self.feedback_options_frame.grid(row=2, column=0, columnspan=4, sticky='w', padx=(25, 0), pady=(8, 0))
        else: 
            self.feedback_options_frame.grid_forget()

    def _toggle_sequence_editor(self):
        self._populate_sequence_listbox()
        if self.search_mode.get() == "sequence":
            self.sequence_frame.grid(row=3, column=0, sticky="ew", pady=10)
        else:
            self.sequence_frame.grid_forget()

    def _choose_color(self, event=None):
        try:
            _, color_hex = colorchooser.askcolor(parent=self.root, initialcolor=self.feedback_color.get())
            if color_hex: 
                self.feedback_color.set(color_hex)
                self.color_swatch.config(bg=color_hex)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open color chooser: {e}")

    def _show_feedback_box(self, box):
        try:
            feedback_window = Toplevel(self.root); feedback_window.overrideredirect(True)
            feedback_window.geometry(f'{box.width}x{box.height}+{box.left}+{box.top}')
            feedback_window.config(bg=self.TRANSPARENT_COLOR); feedback_window.wm_attributes("-transparentcolor", self.TRANSPARENT_COLOR); feedback_window.attributes("-topmost", True)
            border_frame = Frame(feedback_window, highlightbackground=self.feedback_color.get(), highlightthickness=3, bg=self.TRANSPARENT_COLOR)
            border_frame.pack(fill="both", expand=True); self.root.update_idletasks()
            return feedback_window
        except Exception:
            return None

    def _start_capture_mode(self):
        if not self.active_profile.get(): 
            messagebox.showwarning("No Profile Selected", "Please select or create a profile before adding a template.")
            return
        
        try:
            self.root.withdraw()
            self.capture_window = Toplevel(self.root)
            self.capture_window.attributes("-fullscreen", True)
            self.capture_window.attributes("-alpha", 0.3)
            self.capture_window.attributes("-topmost", True)
            self.capture_window.focus_set()
            
            self.capture_canvas = Canvas(self.capture_window, cursor="cross", bg="grey")
            self.capture_canvas.pack(fill="both", expand=True)
            self.capture_canvas.focus_set()
            
            self.rect, self.start_x, self.start_y = None, None, None
            self.capture_canvas.bind("<Button-1>", self._on_capture_press)
            self.capture_canvas.bind("<B1-Motion>", self._on_capture_drag)
            self.capture_canvas.bind("<ButtonRelease-1>", self._on_capture_release)
            self.capture_window.bind("<KeyPress-Escape>", self._cancel_capture)
            self.capture_canvas.bind("<KeyPress-Escape>", self._cancel_capture)
            
        except Exception as e:
            self.root.deiconify()
            messagebox.showerror("Error", f"Could not start capture mode: {e}")

    def _cancel_capture(self, event=None):
        try:
            if hasattr(self, 'capture_window') and self.capture_window.winfo_exists():
                self.capture_window.destroy()
        except Exception:
            pass
        finally:
            self.root.deiconify()

    def _on_capture_press(self, event):
        self.start_x, self.start_y = self.capture_canvas.canvasx(event.x), self.capture_canvas.canvasy(event.y)
        self.rect = self.capture_canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2)

    def _on_capture_drag(self, event):
        cur_x, cur_y = self.capture_canvas.canvasx(event.x), self.capture_canvas.canvasy(event.y)
        self.capture_canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def _on_capture_release(self, event):
        try:
            end_x, end_y = self.capture_canvas.canvasx(event.x), self.capture_canvas.canvasy(event.y)
            self.capture_window.destroy()
            x1, y1, x2, y2 = min(self.start_x, end_x), min(self.start_y, end_y), max(self.start_x, end_x), max(self.start_y, end_y)
            width, height = x2 - x1, y2 - y1
            
            if width > self.MIN_CAPTURE_SIZE and height > self.MIN_CAPTURE_SIZE:
                region_tuple = (int(x1), int(y1), int(width), int(height))
                img = pyautogui.screenshot(region=region_tuple)
                profile_dir = Path(self.profiles_root_path.get()) / self.active_profile.get()
                profile_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = profile_dir / f"template_{timestamp}.png"
                img.save(save_path)
                
                self.template_cache.clear_cache()
                self._populate_sequence_listbox()
                messagebox.showinfo("Success", f"Template saved to profile '{self.active_profile.get()}':\n{save_path}")
            else:
                messagebox.showwarning("Capture Too Small", f"Please capture an area larger than {self.MIN_CAPTURE_SIZE}x{self.MIN_CAPTURE_SIZE} pixels.")
        except Exception as e: 
            messagebox.showerror("Error", f"Failed to save template: {e}")
        finally:
            self.root.deiconify()

    def _log(self, message: str, level: str = "INFO"):
        if not self.log_text_widget: return
        try:
            self.log_text_widget.config(state="normal")
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.log_text_widget.insert("end", f"[{timestamp}][{level}] {message}\n")
            self.log_text_widget.see("end")
            self.log_text_widget.config(state="disabled")
        except Exception:
            pass

    def _load_config(self):
        try:
            with open(self.CONFIG_FILE, "r") as f: 
                self.config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): 
            self.config = {}
        
        self.profiles_root_path.set(self.config.get("profiles_root_path", "profiles"))
        self.active_profile.set(self.config.get("active_profile", ""))
        self.always_on_top.set(self.config.get("always_on_top", False))
        self.show_visual_feedback.set(self.config.get("show_visual_feedback", False))
        self.feedback_color.set(self.config.get("feedback_color", "#00FF00"))
        self.feedback_duration.set(self.config.get("feedback_duration", 400))
        self._load_profile_settings()
        self._last_active_profile = self.active_profile.get()

    def _save_config(self):
        try:
            self._save_current_profile_settings()
            self.config["profiles_root_path"] = self.profiles_root_path.get()
            self.config["active_profile"] = self.active_profile.get()
            self.config["always_on_top"] = self.always_on_top.get()
            self.config["show_visual_feedback"] = self.show_visual_feedback.get()
            self.config["feedback_color"] = self.feedback_color.get()
            self.config["feedback_duration"] = self.feedback_duration.get()
            with open(self.CONFIG_FILE, "w") as f: 
                json.dump(self.config, f, indent=4)
        except Exception:
            pass

    def _validate_inputs(self) -> bool:
        try:
            if not self.active_profile.get(): 
                messagebox.showerror("Invalid Setup", "No active profile selected. Please select or create a profile.")
                return False
            
            confidence = self.confidence.get()
            if not (0.0 <= confidence <= 1.0):
                messagebox.showerror("Invalid Input", "Confidence must be between 0.0 and 1.0.")
                return False
                
            min_sleep = self.min_sleep_seconds.get()
            max_sleep = self.max_sleep_seconds.get()
            if min_sleep < 0 or max_sleep < 0:
                messagebox.showerror("Invalid Input", "Sleep values must be positive.")
                return False
            if min_sleep > max_sleep:
                messagebox.showerror("Invalid Input", "Minimum sleep must be less than or equal to maximum sleep.")
                return False
                
            duration = self.feedback_duration.get()
            if duration < 0:
                messagebox.showerror("Invalid Input", "Feedback duration must be positive.")
                return False
                
            return True
        except (ValueError, TypeError):
            messagebox.showerror("Invalid Input", "Please ensure all numeric fields contain valid numbers.")
            return False

    def _on_press(self, key):
        try:
            if key == keyboard.Key.f3: 
                self.root.after_idle(self._start_handler)
            elif key == keyboard.Key.f4: 
                self.root.after_idle(self._pause_handler)
            elif key == keyboard.Key.esc and hasattr(self, 'capture_window'):
                self.root.after_idle(self._cancel_capture)
        except Exception:
            pass

    def _select_profiles_root(self):
        try:
            path = filedialog.askdirectory(title="Select Profiles Root Directory")
            if path: 
                self.profiles_root_path.set(path)
                self._update_profile_list()
        except Exception as e:
            messagebox.showerror("Error", f"Could not change profiles directory: {e}")

    def get_profiles(self) -> list:
        try:
            root_path = Path(self.profiles_root_path.get())
            if not root_path.is_dir(): 
                return []
            return [d.name for d in root_path.iterdir() if d.is_dir()]
        except Exception:
            return []

    def _update_profile_list(self):
        try:
            profiles = sorted(self.get_profiles())
            self.profile_combobox['values'] = profiles
            saved_profile = self.active_profile.get()
            if saved_profile in profiles: 
                self.profile_combobox.set(saved_profile)
            elif profiles: 
                self.profile_combobox.set(profiles[0])
                self.active_profile.set(profiles[0])
            else: 
                self.profile_combobox.set("")
                self.active_profile.set("")
            self._on_profile_change()
        except Exception:
            pass

    def _on_profile_change(self, event=None):
        try:
            if self._last_active_profile and self._last_active_profile != self.active_profile.get():
                self._save_current_profile_settings()
            
            self.template_cache.clear_cache()
            self._load_profile_settings()
            self._populate_sequence_listbox()
            self._last_active_profile = self.active_profile.get()
        except Exception:
            pass

    def _populate_sequence_listbox(self):
        try:
            self.sequence_listbox.delete(0, 'end')
            profile_name = self.active_profile.get()
            if not profile_name: 
                return
            
            profile_path = Path(self.profiles_root_path.get()) / profile_name
            if not profile_path.is_dir(): 
                return
            
            actual_files = {p.name for p in profile_path.iterdir() if p.is_file()}
            profile_settings = self.config.get("profile_settings", {}).get(profile_name, {})
            saved_sequence = profile_settings.get("sequence", [])
            final_sequence = [f for f in saved_sequence if f in actual_files]
            new_files = sorted([f for f in actual_files if f not in final_sequence])
            final_sequence.extend(new_files)
            
            for item in final_sequence: 
                self.sequence_listbox.insert('end', item)
        except Exception:
            pass

    def _move_template_up(self):
        try:
            selected_indices = self.sequence_listbox.curselection()
            if not selected_indices: 
                return
            idx = selected_indices[0]
            if idx > 0:
                item = self.sequence_listbox.get(idx)
                self.sequence_listbox.delete(idx)
                self.sequence_listbox.insert(idx - 1, item)
                self.sequence_listbox.selection_set(idx - 1)
                self.sequence_listbox.activate(idx - 1)
        except Exception:
            pass

    def _move_template_down(self):
        try:
            selected_indices = self.sequence_listbox.curselection()
            if not selected_indices: 
                return
            idx = selected_indices[0]
            if idx < self.sequence_listbox.size() - 1:
                item = self.sequence_listbox.get(idx)
                self.sequence_listbox.delete(idx)
                self.sequence_listbox.insert(idx + 1, item)
                self.sequence_listbox.selection_set(idx + 1)
                self.sequence_listbox.activate(idx + 1)
        except Exception:
            pass

    def _create_new_profile(self, parent_window=None):
        parent = parent_window if parent_window else self.root
        try:
            new_profile_name = simpledialog.askstring("New Profile", "Enter a name for the new profile:", parent=parent)
            if not new_profile_name or not new_profile_name.strip(): 
                return
            
            if any(char in new_profile_name for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
                messagebox.showerror("Invalid Name", "Profile name contains invalid characters.", parent=parent)
                return
            
            root_path = Path(self.profiles_root_path.get())
            root_path.mkdir(exist_ok=True)
            new_profile_path = root_path / new_profile_name
            if new_profile_path.exists(): 
                messagebox.showwarning("Profile Exists", f"A profile named '{new_profile_name}' already exists.", parent=parent)
                return
            
            new_profile_path.mkdir(parents=True, exist_ok=True)
            self.active_profile.set(new_profile_name)
            self._update_profile_list()
            self._populate_sequence_listbox()
            messagebox.showinfo("Success", f"Profile '{new_profile_name}' created successfully.", parent=parent)
        except Exception as e: 
            messagebox.showerror("Error", f"Could not create profile directory: {e}", parent=parent)

    def _open_profile_manager(self):
        try:
            ProfileManagerWindow(self)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open profile manager: {e}")

    def _update_always_on_top(self):
        try:
            is_on_top = self.always_on_top.get()
            self.root.attributes("-topmost", is_on_top)
            if self.log_window and self.log_window.winfo_exists(): 
                self.log_window.attributes("-topmost", is_on_top)
        except Exception:
            pass

    def _start_handler(self):
        if self._is_running: 
            return
        if not self._validate_inputs(): 
            return
        
        try:
            self._is_running = True
            self.start_button.config(state="disabled", text="Running...")
            self.sequence_index = 0
            
            if self.log_window is None: 
                self._show_log_window()
            self._load_templates()
            if self.log_window: 
                self.root.withdraw()
            self._match_loop()
        except Exception as e:
            self._is_running = False
            self.start_button.config(state="normal", text="Start (F3)")
            messagebox.showerror("Error", f"Could not start automation: {e}")

    def _pause_handler(self):
        if not self._is_running: 
            return
        try:
            self._is_running = False
            if self._after_id: 
                self.root.after_cancel(self._after_id)
            self.start_button.config(state="normal", text="Resume (F3)")
            self.root.deiconify()
            self._log("Process paused. Press F3 to resume.", "WARN")
        except Exception:
            pass

    def _load_templates(self):
        try:
            self.templates.clear()
            profile_path = Path(self.profiles_root_path.get()) / self.active_profile.get()
            if not profile_path.is_dir(): 
                return
            
            all_template_files = sorted([p for p in profile_path.iterdir() if p.is_file()], key=_human_sort)
            loaded_count = 0
            
            for path in all_template_files:
                template = self.template_cache.get_template(path)
                if template:
                    self.templates[path.name] = template
                    loaded_count += 1

            stats = self.template_cache.get_cache_stats()
            self._log(f"Loaded {loaded_count} templates for profile '{self.active_profile.get()}'")
            if loaded_count > 0:
                self._log(f"Cache: {stats['cache_size']}/{stats['max_size']} (Hit rate: {stats['hit_rate']:.1f}%)")
        except Exception as e:
            self._log(f"Error loading templates: {e}", "ERROR")

    def _match_loop(self):
        if not self._is_running: 
            return
        try:
            self._perform_match()
            sleep_interval = random.uniform(self.min_sleep_seconds.get(), self.max_sleep_seconds.get())
            self._log(f"Waiting for {sleep_interval:.2f} seconds.")
            self._after_id = self.root.after(int(sleep_interval * 1000), self._match_loop)
        except Exception as e:
            self._log(f"Error in match loop: {e}", "ERROR")
            self._pause_handler()

    def _perform_click_action(self, box, path_name):
        try:
            center_x, center_y = pyautogui.center(box)
            click_x = center_x + random.randint(-self.CLICK_TOLERANCE, self.CLICK_TOLERANCE)
            click_y = center_y + random.randint(-self.CLICK_TOLERANCE, self.CLICK_TOLERANCE)
            original_pos = pyautogui.position()
            pyautogui.click(click_x, click_y)
            pyautogui.moveTo(original_pos)
            self._log(f"Clicked {path_name} at ({click_x}, {click_y})", "INFO")
        except Exception as e:
            self._log(f"Error clicking {path_name}: {e}", "ERROR")

    def _perform_match(self):
        try:
            if not self.templates:
                self._log(f"No templates loaded for profile '{self.active_profile.get()}'. Pausing.", "WARN")
                self._pause_handler()
                return
            
            screenshot = pyautogui.screenshot()
            if self.search_mode.get() == "sequence": 
                self._perform_match_sequence(screenshot)
            else: 
                self._perform_match_priority(screenshot)
        except Exception as e:
            self._log(f"Screenshot error: {e}. Retrying...", "WARN")

    def _perform_match_priority(self, screenshot):
        try:
            search_kwargs: Dict[str, Any] = {"grayscale": self.grayscale.get()}
            if has_cv2: 
                search_kwargs["confidence"] = self.confidence.get()
            
            sorted_template_names = sorted(self.templates.keys(), key=str.lower)
            for name in sorted_template_names:
                image = self.templates.get(name)
                if not image: 
                    continue
                
                self._log(f"Attempting to find {name}.")
                try:
                    box = pyautogui.locate(image, screenshot, **search_kwargs)
                    if box: 
                        self._handle_found_match(box, name)
                        return
                except pyautogui.PyAutoGUIException as e: 
                    self._log(f"Search error for {name}: {e}", "WARN")
        except Exception as e:
            self._log(f"Error in priority match: {e}", "ERROR")

    def _perform_match_sequence(self, screenshot):
        try:
            sequence = list(self.sequence_listbox.get(0, 'end'))
            if not sequence: 
                self._log("Sequence is empty. Pausing.", "WARN")
                self._pause_handler()
                return
            
            self.sequence_index %= len(sequence)
            target_name = sequence[self.sequence_index]
            image_to_find = self.templates.get(target_name)
            
            if not image_to_find: 
                self._log(f"Template '{target_name}' for sequence step not found in memory. Pausing.", "FATAL")
                self._pause_handler()
                return
            
            self._log(f"Searching for sequence step {self.sequence_index + 1}/{len(sequence)}: '{target_name}'.")
            search_kwargs: Dict[str, Any] = {"grayscale": self.grayscale.get()}
            if has_cv2: 
                search_kwargs["confidence"] = self.confidence.get()
            
            box = pyautogui.locate(image_to_find, screenshot, **search_kwargs)
            if box:
                self.sequence_index = (self.sequence_index + 1) % len(sequence)
                self._handle_found_match(box, target_name)
        except pyautogui.PyAutoGUIException as e: 
            self._log(f"Search error for sequence: {e}", "WARN")
        except Exception as e:
            self._log(f"Error in sequence match: {e}", "ERROR")

    def _handle_found_match(self, box, path_name):
        try:
            if self.show_visual_feedback.get():
                feedback_box = self._show_feedback_box(box)
                if feedback_box:
                    self.root.after(self.feedback_duration.get(), lambda: (
                        feedback_box.destroy(), self._perform_click_action(box, path_name)
                    ))
                else:
                    self._perform_click_action(box, path_name)
            else:
                self._perform_click_action(box, path_name)
        except Exception as e:
            self._log(f"Error handling match for {path_name}: {e}", "ERROR")

    def _show_log_window(self):
        try:
            self.root.withdraw()
            self.log_window = Toplevel(self.root)
            self.log_window.title("Log Console")
            self.log_window.protocol("WM_DELETE_WINDOW", self._terminate_app)
            self.log_window.config(bg=self.BG_COLOR)
            self.log_window.geometry("800x400")
            self._update_always_on_top()
            
            main_log_frame = Frame(self.log_window, bg=self.BG_COLOR)
            main_log_frame.pack(padx=10, pady=10, fill="both", expand=True)
            
            help_label = Label(main_log_frame, text="F3: Resume | F4: Pause & Show Settings", 
                             bg=self.BG_COLOR, fg=self.SECONDARY_FG_COLOR, font=("Segoe UI", 9))
            help_label.pack(pady=(0, 5))
            
            text_frame = Frame(main_log_frame, bg=self.BG_COLOR)
            text_frame.pack(fill="both", expand=True)
            
            self.log_text_widget = Text(text_frame, height=15, width=80, wrap="word", 
                                       bg=self.INPUT_BG_COLOR, fg=self.FG_COLOR, bd=0, 
                                       highlightthickness=0, font=("Consolas", 9))
            self.log_text_widget.pack(side="left", fill="both", expand=True)
            
            scrollbar = Scrollbar(text_frame, command=self.log_text_widget.yview, 
                                bg=self.BG_COLOR, troughcolor=self.INPUT_BG_COLOR, bd=0, 
                                activebackground=self.BUTTON_ACTIVE_BG_COLOR)
            scrollbar.pack(side="right", fill="y")
            self.log_text_widget.config(yscrollcommand=scrollbar.set, state="disabled")
            
            self._log(f"Activating profile: '{self.active_profile.get()}' with search mode: '{self.search_mode.get()}'")
            self._log("Process started. Starting search loop...")
            
            if not has_cv2:
                self._log("Note: Confidence setting is ignored because OpenCV is not installed. Run: pip install opencv-python", "WARN")
        except Exception as e:
            messagebox.showerror("Error", f"Could not show log window: {e}")

    def _terminate_app(self):
        try:
            self._save_config()
            self._is_running = False
            if self._after_id: 
                self.root.after_cancel(self._after_id)
            if hasattr(self, 'keyboard_listener') and self.keyboard_listener.is_alive(): 
                self.keyboard_listener.stop()
            self.root.destroy()
        except Exception:
            pass

    def _load_profile_settings(self):
        try:
            profile_name = self.active_profile.get()
            if not profile_name:
                profile_settings = {}
            else:
                all_profile_settings = self.config.get("profile_settings", {})
                profile_settings = all_profile_settings.get(profile_name, {})
            
            self.confidence.set(profile_settings.get("confidence", 0.8))
            self.grayscale.set(profile_settings.get("grayscale", True))
            self.min_sleep_seconds.set(profile_settings.get("min_sleep", 1.0))
            self.max_sleep_seconds.set(profile_settings.get("max_sleep", 5.0))
            self.search_mode.set(profile_settings.get("search_mode", "priority"))
        except Exception:
            pass

    def _save_current_profile_settings(self):
        try:
            profile_name = self._last_active_profile
            if not profile_name: 
                return
            
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
        except Exception:
            pass

    def _rename_profile_config(self, old_name, new_name):
        try:
            if "profile_settings" in self.config and old_name in self.config["profile_settings"]:
                self.config["profile_settings"][new_name] = self.config["profile_settings"].pop(old_name)
        except Exception:
            pass

    def _delete_profile_config(self, profile_name):
        try:
            if "profile_settings" in self.config:
                self.config["profile_settings"].pop(profile_name, None)
        except Exception:
            pass

if __name__ == "__main__":
    main_root = Tk()
    app = NexusAutoDL(main_root)
    try:
        main_root.mainloop()
    except KeyboardInterrupt:
        app._terminate_app()
