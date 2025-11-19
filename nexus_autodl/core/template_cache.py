"""
Template cache management for Nexus AutoDL.
"""

import gc
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from PIL import Image, UnidentifiedImageError
from PIL.Image import open as open_image

from ..constants import AppConstants
from ..utils.helpers import safe_path_operation

class EnhancedTemplateCache:
    def __init__(self, max_cache_size: int = AppConstants.CACHE_SIZE):
        self._cache: Dict[str, Image.Image] = {}
        self._timestamps: Dict[str, float] = {}
        self._access_order: List[str] = []
        self._max_size = max_cache_size
        self._cache_hits = 0
        self._cache_misses = 0
        self._lock = threading.RLock()
    
    @safe_path_operation
    def get_template(self, template_path: Path) -> Optional[Image.Image]:
        if not template_path or not template_path.exists():
            return None
        
        path_str = str(template_path)
        
        with self._lock:
            try:
                file_mtime = template_path.stat().st_mtime
                
                if (path_str in self._cache and 
                    path_str in self._timestamps and 
                    self._timestamps[path_str] >= file_mtime):
                    
                    self._update_access_order(path_str)
                    self._cache_hits += 1
                    return self._cache[path_str].copy()
                
                template = self._load_template_safely(template_path)
                if template:
                    self._store_template(path_str, template, file_mtime)
                    self._cache_misses += 1
                    return template.copy()
                
            except Exception as e:
                print(f"Error loading template {template_path}: {e}")
                return None
    
    def _load_template_safely(self, template_path: Path) -> Optional[Image.Image]:
        try:
            with open_image(template_path) as img:
                if img.mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')
                return img.copy()
        except (UnidentifiedImageError, OSError, IOError) as e:
            print(f"Failed to load image {template_path}: {e}")
            return None
    
    def _store_template(self, path_str: str, template: Image.Image, mtime: float):
        if path_str in self._cache:
            self._remove_from_cache(path_str)
        
        while len(self._cache) >= self._max_size and self._access_order:
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
        if path_str in self._cache:
            try:
                self._cache[path_str].close()
            except Exception:
                pass
        
        self._cache.pop(path_str, None)
        self._timestamps.pop(path_str, None)
        if path_str in self._access_order:
            self._access_order.remove(path_str)
    
    def invalidate_template(self, template_path: Path):
        if not template_path:
            return
        
        path_str = str(template_path)
        with self._lock:
            self._remove_from_cache(path_str)
    
    def clear_cache(self):
        with self._lock:
            for img in self._cache.values():
                try:
                    img.close()
                except Exception:
                    pass
            
            self._cache.clear()
            self._timestamps.clear()
            self._access_order.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            gc.collect()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
            
            memory_usage = sum(
                img.width * img.height * len(img.getbands()) 
                for img in self._cache.values()
            ) if self._cache else 0
            
            return {
                'cache_size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._cache_hits,
                'misses': self._cache_misses,
                'hit_rate': hit_rate,
                'memory_usage_bytes': memory_usage,
                'cached_templates': list(self._cache.keys())
            }
