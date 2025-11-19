"""
Secondary windows for Nexus AutoDL.
"""

from pathlib import Path
from typing import Tuple
from tkinter import Toplevel, Frame, Label, Button, Entry, LabelFrame, Listbox, Scrollbar, messagebox
from PIL import Image, ImageTk
from PIL.Image import open as open_image

from ..constants import AppConstants
from .theme_manager import ThemeManager
from .components import OptimizedHoverEffect

class EnhancedTemplatePreviewWindow(Toplevel):
    def __init__(self, parent, template_path: Path, theme_manager: ThemeManager):
        super().__init__(parent)
        self.parent = parent
        self.template_path = template_path  
        self.theme_manager = theme_manager
        self.photo = None
        
        self._configure_window()
        
        try:
            self._setup_ui()
            self._center_window()
        except Exception as e:
            self.destroy()
            messagebox.showerror(
                "Preview Error", 
                f"Unable to load template preview for '{template_path.name}'\n\nError: {str(e)}", 
                parent=parent
            )
    
    def _configure_window(self):
        self.title(f"Template Preview - {self.template_path.name}")
        self.config(bg=self.theme_manager.get_color('preview_bg_color'))
        self.resizable(False, False)
        self.transient(self.parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _on_close(self):
        if self.photo:
            try:
                del self.photo
            except Exception:
                pass
        self.destroy()
    
    def _setup_ui(self):
        try:
            img, original_size = self._load_and_resize_image()
            self.photo = ImageTk.PhotoImage(img)
            
            main_frame = Frame(self, bg=self.theme_manager.get_color('preview_bg_color'), padx=20, pady=20)
            main_frame.pack(fill="both", expand=True)
            
            self._create_info_section(main_frame, original_size, img.size)
            self._create_image_section(main_frame)
            self._create_button_section(main_frame)
            
        except Exception as e:
            self._create_error_ui(str(e))
    
    def _load_and_resize_image(self) -> Tuple[Image.Image, Tuple[int, int]]:
        with open_image(self.template_path) as img:
            original_size = (img.width, img.height)
            
            max_size = 400
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            return img.copy(), original_size
    
    def _create_info_section(self, parent, original_size, current_size):
        info_frame = Frame(parent, bg=self.theme_manager.get_color('preview_bg_color'))
        info_frame.pack(fill="x", pady=(0, 15))
        
        Label(info_frame, text=f"File: {self.template_path.name}", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('fg_color'), 
              font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        Label(info_frame, text=f"Original Size: {original_size[0]}×{original_size[1]} pixels", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('secondary_fg_color'), 
              font=("Segoe UI", 9)).pack(anchor="w")
        
        if current_size != original_size:
            Label(info_frame, text=f"Preview Size: {current_size[0]}×{current_size[1]} pixels (scaled)", 
                  bg=self.theme_manager.get_color('preview_bg_color'), 
                  fg=self.theme_manager.get_color('secondary_fg_color'), 
                  font=("Segoe UI", 9)).pack(anchor="w")
    
    def _create_image_section(self, parent):
        image_frame = Frame(parent, bg=self.theme_manager.get_color('input_bg_color'), 
                           relief="solid", bd=1)
        image_frame.pack(pady=15)
        
        image_label = Label(image_frame, image=self.photo, 
                           bg=self.theme_manager.get_color('input_bg_color'))
        image_label.pack(padx=8, pady=8)
    
    def _create_button_section(self, parent):
        close_btn = Button(parent, text="Close", command=self._on_close,
                          bg=self.theme_manager.get_color('button_bg_color'), 
                          fg=self.theme_manager.get_color('button_fg_color'), 
                          bd=0, padx=30, pady=8, 
                          font=("Segoe UI", 9), cursor="hand2", relief="flat")
        close_btn.pack(pady=(20, 0))
        
        OptimizedHoverEffect(close_btn, 'close', self.theme_manager)
    
    def _create_error_ui(self, error_message: str):
        error_frame = Frame(self, bg=self.theme_manager.get_color('preview_bg_color'), 
                           padx=40, pady=40)
        error_frame.pack(fill="both", expand=True)
        
        Label(error_frame, text="⚠", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('error_fg_color'), 
              font=("Segoe UI", 24)).pack(pady=(0, 10))
        
        Label(error_frame, text="Unable to load image preview", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('error_fg_color'), 
              font=("Segoe UI", 11, "bold")).pack(pady=(0, 5))
        
        Label(error_frame, text=f"Error: {error_message}", 
              bg=self.theme_manager.get_color('preview_bg_color'), 
              fg=self.theme_manager.get_color('fg_color'), 
              font=("Segoe UI", 9)).pack(pady=(0, 20))
        
        close_btn = Button(error_frame, text="Close", command=self._on_close,
                          bg=self.theme_manager.get_color('button_bg_color'), 
                          fg=self.theme_manager.get_color('button_fg_color'), 
                          bd=0, padx=30, pady=8, 
                          font=("Segoe UI", 9), cursor="hand2", relief="flat")
        close_btn.pack()
        
        OptimizedHoverEffect(close_btn, 'close', self.theme_manager)
    
    def _center_window(self):
        self.update_idletasks()
        
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        my_width = self.winfo_width()
        my_height = self.winfo_height()
        
        pos_x = parent_x + (parent_width - my_width) // 2
        pos_y = parent_y + (parent_height - my_height) // 2
        
        pos_x = max(0, pos_x)
        pos_y = max(0, pos_y)
        
        self.geometry(f"+{pos_x}+{pos_y}")

class EnhancedProfileManagerWindow(Toplevel):
    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.parent_app = parent_app
        self.theme_manager = parent_app.theme_manager
        
        self._configure_window()
        self._setup_ui()
        self._populate_profile_list()
        self._center_window()
    
    def _configure_window(self):
        self.transient(self.parent_app.root)
        self.title("Profile & Template Manager")
        self.config(bg=self.theme_manager.get_color('bg_color'))
        self.resizable(True, True)
        self.grab_set()
        self.minsize(600, 450)
    
    def _center_window(self):
        self.update_idletasks()
        parent = self.parent_app.root
        
        width, height = map(int, AppConstants.PROFILE_MANAGER_SIZE.split('x'))
        
        parent_x, parent_y = parent.winfo_x(), parent.winfo_y()
        parent_width, parent_height = parent.winfo_width(), parent.winfo_height()
        
        pos_x = parent_x + (parent_width - width) // 2
        pos_y = parent_y + (parent_height - height) // 2
        
        pos_x = max(0, pos_x)
        pos_y = max(0, pos_y)
        
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
    
    def _setup_ui(self):
        main_frame = Frame(self, bg=self.theme_manager.get_color('bg_color'))
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        self._create_header(main_frame)
        self._create_directory_section(main_frame)
        self._create_content_section(main_frame)
    
    def _create_header(self, parent):
        header_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        header_frame.pack(fill="x", pady=(0, 15))
        
        title_label = Label(header_frame, text="Profile & Template Manager", 
                           bg=self.theme_manager.get_color('bg_color'), 
                           fg=self.theme_manager.get_color('fg_color'), 
                           font=("Segoe UI", 13, "bold"))
        title_label.pack(side="left")
    
    def _create_directory_section(self, parent):
        dir_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        dir_frame.pack(fill="x", pady=(0, 15))
        
        Label(dir_frame, text="Profiles Directory:", 
              bg=self.theme_manager.get_color('bg_color'), 
              fg=self.theme_manager.get_color('fg_color'), 
              font=("Segoe UI", 10)).pack(side="left")
        
        path_entry = Entry(dir_frame, textvariable=self.parent_app.profiles_root_path, 
                          state="readonly", 
                          readonlybackground=self.theme_manager.get_color('readonly_bg_color'), 
                          fg=self.theme_manager.get_color('input_fg_color'), 
                          bd=1, font=("Segoe UI", 9))
        path_entry.pack(side="left", fill="x", expand=True, padx=(10, 10))
        
        browse_btn = Button(dir_frame, text="Browse...", command=self._select_profiles_root, 
                           bg=self.theme_manager.get_color('button_bg_color'), 
                           fg=self.theme_manager.get_color('button_fg_color'), 
                           bd=0, padx=15, pady=6, font=("Segoe UI", 9), 
                           cursor="hand2", relief="flat")
        browse_btn.pack(side="right")
        
        OptimizedHoverEffect(browse_btn, 'browse', self.theme_manager)
    
    def _create_content_section(self, parent):
        content_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        content_frame.pack(fill="both", expand=True)
        
        self._create_profiles_panel(content_frame)
        self._create_templates_panel(content_frame)
    
    def _create_profiles_panel(self, parent):
        left_panel = LabelFrame(parent, text="Profiles", 
                               bg=self.theme_manager.get_color('bg_color'), 
                               fg=self.theme_manager.get_color('fg_color'), 
                               padx=10, pady=10, 
                               font=("Segoe UI", 10, "bold"))
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        profile_list_frame = Frame(left_panel, bg=self.theme_manager.get_color('bg_color'))
        profile_list_frame.pack(fill="both", expand=True)
        
        self.profile_listbox = Listbox(profile_list_frame, 
                                      bg=self.theme_manager.get_color('input_bg_color'), 
                                      fg=self.theme_manager.get_color('input_fg_color'), 
                                      bd=0, highlightthickness=0, 
                                      selectbackground=self.theme_manager.get_color('selection_bg_color'), 
                                      selectforeground=self.theme_manager.get_color('selection_fg_color'),
                                      exportselection=False, font=("Segoe UI", 9))
        self.profile_listbox.pack(side="left", fill="both", expand=True)
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)
        self.profile_listbox.bind("<Double-Button-1>", self._set_active_profile)
        
        profile_scrollbar = Scrollbar(profile_list_frame, command=self.profile_listbox.yview,
                                     bg=self.theme_manager.get_color('bg_color'),
                                     troughcolor=self.theme_manager.get_color('input_bg_color'),
                                     activebackground=self.theme_manager.get_color('selection_bg_color'))
        profile_scrollbar.pack(side="right", fill="y")
        self.profile_listbox.config(yscrollcommand=profile_scrollbar.set)

        self._create_profile_buttons(left_panel)
    
    def _create_profile_buttons(self, parent):
        profile_buttons_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        profile_buttons_frame.pack(fill="x", pady=(10, 0))
        
        button_style = {
            "bg": self.theme_manager.get_color('button_bg_color'), 
            "fg": self.theme_manager.get_color('button_fg_color'), 
            "bd": 0, "padx": 12, "pady": 5, 
            "font": ("Segoe UI", 9), "cursor": "hand2", "relief": "flat"
        }
        
        new_btn = Button(profile_buttons_frame, text="New", command=self._create_profile, **button_style)
        new_btn.pack(side="left")
        OptimizedHoverEffect(new_btn, 'new', self.theme_manager)
        
        rename_btn = Button(profile_buttons_frame, text="Rename", command=self._rename_profile, **button_style)
        rename_btn.pack(side="left", padx=(6,0))
        OptimizedHoverEffect(rename_btn, 'rename', self.theme_manager)
        
        delete_btn = Button(profile_buttons_frame, text="Delete", command=self._delete_profile, **button_style)
        delete_btn.pack(side="left", padx=(6,0))
        OptimizedHoverEffect(delete_btn, 'delete', self.theme_manager)
        
        set_active_btn = Button(profile_buttons_frame, text="Set Active", 
                               command=self._set_active_profile, **button_style)
        set_active_btn.pack(side="right")
        OptimizedHoverEffect(set_active_btn, 'set_active', self.theme_manager)
    
    def _create_templates_panel(self, parent):
        right_panel = LabelFrame(parent, text="Templates", 
                                bg=self.theme_manager.get_color('bg_color'), 
                                fg=self.theme_manager.get_color('fg_color'), 
                                padx=10, pady=10, 
                                font=("Segoe UI", 10, "bold"))
        right_panel.pack(side="right", fill="both", expand=True, padx=(8, 0))
        
        template_list_frame = Frame(right_panel, bg=self.theme_manager.get_color('bg_color'))
        template_list_frame.pack(fill="both", expand=True)
        
        self.template_listbox = Listbox(template_list_frame, 
                                       bg=self.theme_manager.get_color('input_bg_color'), 
                                       fg=self.theme_manager.get_color('input_fg_color'), 
                                       bd=0, highlightthickness=0, 
                                       selectbackground=self.theme_manager.get_color('selection_bg_color'), 
                                       selectforeground=self.theme_manager.get_color('selection_fg_color'),
                                       exportselection=False, font=("Segoe UI", 9))
        self.template_listbox.pack(side="left", fill="both", expand=True)
        self.template_listbox.bind("<Double-Button-1>", self._preview_template)
        
        template_scrollbar = Scrollbar(template_list_frame, command=self.template_listbox.yview,
                                      bg=self.theme_manager.get_color('bg_color'),
                                      troughcolor=self.theme_manager.get_color('input_bg_color'),
                                      activebackground=self.theme_manager.get_color('selection_bg_color'))
        template_scrollbar.pack(side="right", fill="y")
        self.template_listbox.config(yscrollcommand=template_scrollbar.set)
        
        self._create_template_buttons(right_panel)
        
    def _create_template_buttons(self, parent):
        template_buttons_frame = Frame(parent, bg=self.theme_manager.get_color('bg_color'))
        template_buttons_frame.pack(fill="x", pady=(10, 0))
        
        button_style = {
            "bg": self.theme_manager.get_color('button_bg_color'), 
            "fg": self.theme_manager.get_color('button_fg_color'), 
            "bd": 0, "padx": 12, "pady": 5, 
            "font": ("Segoe UI", 9), "cursor": "hand2", "relief": "flat"
        }
        
        preview_btn = Button(template_buttons_frame, text="Preview", command=self._preview_template, **button_style)
        preview_btn.pack(side="left")
        OptimizedHoverEffect(preview_btn, 'preview', self.theme_manager)
        
        delete_tmpl_btn = Button(template_buttons_frame, text="Delete", command=self._delete_template, **button_style)
        delete_tmpl_btn.pack(side="right")
        OptimizedHoverEffect(delete_tmpl_btn, 'delete', self.theme_manager)
    
    def _populate_profile_list(self):
        self.profile_listbox.delete(0, 'end')
        profiles = self.parent_app._get_profiles()
        
        active_profile = self.parent_app.active_profile.get()
        
        for i, profile in enumerate(profiles):
            display_name = profile
            if profile == active_profile:
                display_name += " (Active)"
            self.profile_listbox.insert('end', display_name)
            
            if profile == active_profile:
                self.profile_listbox.itemconfig(i, {'fg': self.theme_manager.get_color('success_fg_color')})
    
    def _on_profile_select(self, event):
        selection = self.profile_listbox.curselection()
        if not selection:
            return
            
        profile_display = self.profile_listbox.get(selection[0])
        profile_name = profile_display.replace(" (Active)", "")
        
        self._populate_template_list(profile_name)
    
    def _populate_template_list(self, profile_name):
        self.template_listbox.delete(0, 'end')
        
        profiles_path = Path(self.parent_app.profiles_root_path.get())
        profile_path = profiles_path / profile_name
        
        if not profile_path.exists():
            return
            
        templates = []
        for ext in AppConstants.SUPPORTED_IMAGE_EXTENSIONS:
            templates.extend(profile_path.glob(f"*{ext}"))
            
        for template in sorted(templates, key=lambda p: p.name.lower()):
            self.template_listbox.insert('end', template.name)
    
    def _select_profiles_root(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(parent=self, title="Select Profiles Directory")
        if path:
            self.parent_app.profiles_root_path.set(path)
            self.parent_app._save_config()
            self._populate_profile_list()
            self.template_listbox.delete(0, 'end')
    
    def _create_profile(self):
        # The parent app's method handles the dialog and creation
        self.parent_app._create_new_profile(self)
        self._populate_profile_list()
    
    def _rename_profile(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a profile to rename.", parent=self)
            return
            
        profile_display = self.profile_listbox.get(selection[0])
        old_name = profile_display.replace(" (Active)", "")
        
        from tkinter import simpledialog
        new_name = simpledialog.askstring("Rename Profile", f"Enter new name for '{old_name}':", parent=self)
        
        if not new_name:
            return
            
        new_name = new_name.strip()
        if new_name == old_name:
            return
            
        try:
            from ..utils.helpers import validate_filename
            if not validate_filename(new_name):
                messagebox.showerror("Invalid Name", "Profile name contains invalid characters.", parent=self)
                return
                
            root = Path(self.parent_app.profiles_root_path.get())
            old_path = root / old_name
            new_path = root / new_name
            
            if new_path.exists():
                messagebox.showwarning("Profile Exists", f"A profile named '{new_name}' already exists.", parent=self)
                return
                
            old_path.rename(new_path)
            
            self.parent_app._rename_profile_config(old_name, new_name)
            
            if self.parent_app.active_profile.get() == old_name:
                self.parent_app.active_profile.set(new_name)
            
            self.parent_app._save_config()
            self.parent_app._update_profile_list()
            self._populate_profile_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename profile: {e}", parent=self)
    
    def _delete_profile(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a profile to delete.", parent=self)
            return
            
        profile_display = self.profile_listbox.get(selection[0])
        profile_name = profile_display.replace(" (Active)", "")
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete profile '{profile_name}'?\nThis cannot be undone.", parent=self):
            try:
                import shutil
                root = Path(self.parent_app.profiles_root_path.get())
                shutil.rmtree(root / profile_name)
                
                self.parent_app._delete_profile_config(profile_name)
                
                if self.parent_app.active_profile.get() == profile_name:
                    self.parent_app.active_profile.set("")
                    
                self.parent_app._save_config()
                self.parent_app._update_profile_list()
                self._populate_profile_list()
                self.template_listbox.delete(0, 'end')
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete profile: {e}", parent=self)
    
    def _set_active_profile(self, event=None):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select a profile to set as active.", parent=self)
            return
            
        profile_display = self.profile_listbox.get(selection[0])
        profile_name = profile_display.replace(" (Active)", "")
        
        self.parent_app.active_profile.set(profile_name)
        self.parent_app._save_config()
        self._populate_profile_list()
        
        messagebox.showinfo("Profile Activated", f"Profile '{profile_name}' is now active.", parent=self)
    
    def _preview_template(self, event=None):
        selection = self.profile_listbox.curselection()
        if not selection:
            return
            
        profile_display = self.profile_listbox.get(selection[0])
        profile_name = profile_display.replace(" (Active)", "")
        
        tmpl_selection = self.template_listbox.curselection()
        if not tmpl_selection:
            return
            
        template_name = self.template_listbox.get(tmpl_selection[0])
        
        profiles_path = Path(self.parent_app.profiles_root_path.get())
        template_path = profiles_path / profile_name / template_name
        
        EnhancedTemplatePreviewWindow(self, template_path, self.theme_manager)
    
    def _delete_template(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            return
            
        profile_display = self.profile_listbox.get(selection[0])
        profile_name = profile_display.replace(" (Active)", "")
        
        tmpl_selection = self.template_listbox.curselection()
        if not tmpl_selection:
            messagebox.showwarning("Selection Required", "Please select a template to delete.", parent=self)
            return
            
        template_name = self.template_listbox.get(tmpl_selection[0])
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete template '{template_name}'?", parent=self):
            try:
                profiles_path = Path(self.parent_app.profiles_root_path.get())
                template_path = profiles_path / profile_name / template_name
                
                import os
                os.remove(template_path)
                
                self.parent_app.template_cache.invalidate_template(template_path)
                self._populate_template_list(profile_name)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete template: {e}", parent=self)
