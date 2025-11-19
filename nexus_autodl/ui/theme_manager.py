"""
Theme manager for Nexus AutoDL.
"""

class ThemeManager:
    THEMES = {
        'light': {
            'bg_color': '#F5F5F5',
            'fg_color': '#2C2C2C',
            'input_bg_color': '#FFFFFF',
            'input_fg_color': '#2C2C2C',
            'button_bg_color': '#E0E0E0',
            'button_fg_color': '#2C2C2C',
            'button_active_bg_color': '#D0D0D0',
            'button_active_fg_color': '#1C1C1C',
            'secondary_fg_color': '#666666',
            'border_color': '#C0C0C0',
            'selection_bg_color': '#0078D4',
            'selection_fg_color': '#FFFFFF',
            'tooltip_bg_color': '#FFFFCC',
            'tooltip_fg_color': '#000000',
            'tooltip_border_color': '#CCCCCC',
            'preview_bg_color': '#FAFAFA',
            'preview_border_color': '#DDDDDD',
            'error_fg_color': '#D32F2F',
            'success_fg_color': '#388E3C',
            'readonly_bg_color': '#F8F8F8'
        },
        'dark': {
            'bg_color': '#2E2E2E',
            'fg_color': '#EAEAEA',
            'input_bg_color': '#3C3C3C',
            'input_fg_color': '#EAEAEA',
            'button_bg_color': '#555555',
            'button_fg_color': '#EAEAEA',
            'button_active_bg_color': '#6A6A6A',
            'button_active_fg_color': '#FFFFFF',
            'secondary_fg_color': '#888888',
            'border_color': '#404040',
            'selection_bg_color': '#6A6A6A',
            'selection_fg_color': '#FFFFFF',
            'tooltip_bg_color': '#1E1E1E',
            'tooltip_fg_color': '#EAEAEA',
            'tooltip_border_color': '#404040',
            'preview_bg_color': '#2E2E2E',
            'preview_border_color': '#404040',
            'error_fg_color': '#FF6B6B',
            'success_fg_color': '#4CAF50',
            'readonly_bg_color': '#333333'
        }
    }
    
    HOVER_COLORS = {
        'light': {
            'manage': '#0066CC',
            'create': '#7B1FA2',
            'start': '#2E7D32',
            'new': '#2E7D32',
            'rename': '#F57C00',
            'delete': '#C62828',
            'set_active': '#1976D2',
            'preview': '#7B1FA2',
            'browse': '#0066CC',
            'up': '#2E7D32',
            'down': '#F57C00',
            'close': '#C62828'
        },
        'dark': {
            'manage': '#4A9EFF',
            'create': '#9C27B0',
            'start': '#4CAF50',
            'new': '#4CAF50',
            'rename': '#FF9800',
            'delete': '#F44336',
            'set_active': '#2196F3',
            'preview': '#9C27B0',
            'browse': '#4A9EFF',
            'up': '#4CAF50',
            'down': '#FF9800',
            'close': '#F44336'
        }
    }
    
    def __init__(self, is_dark_mode: bool = False):
        self.is_dark_mode = is_dark_mode
        self._update_theme()
    
    def _update_theme(self):
        theme_key = 'dark' if self.is_dark_mode else 'light'
        self.current_theme = self.THEMES[theme_key]
        self.hover_colors = self.HOVER_COLORS[theme_key]
    
    def switch_theme(self, is_dark_mode: bool) -> bool:
        if self.is_dark_mode != is_dark_mode:
            self.is_dark_mode = is_dark_mode
            self._update_theme()
            return True
        return False
    
    def get_color(self, color_key: str) -> str:
        return self.current_theme.get(color_key, '#000000')
    
    def get_hover_color(self, hover_key: str) -> str:
        if hover_key in self.hover_colors:
            return self.hover_colors[hover_key]
        return self.get_color('button_active_bg_color')
