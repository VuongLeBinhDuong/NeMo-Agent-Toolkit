# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""File content caching for MAS workflow.

This module provides caching functionality to avoid redundant file reads
during workflow execution, improving performance for long-running workflows.
"""

import hashlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .config import get_config

logger = logging.getLogger(__name__)


class FileCache:
    """Cache for file contents with TTL and size limits.
    
    This cache stores file contents to avoid redundant reads during
    workflow execution. It tracks file modification times to invalidate
    stale cache entries.
    """
    
    def __init__(self, max_size: int = 10):
        """Initialize file cache.
        
        Args:
            max_size: Maximum number of files to cache
        """
        self.max_size = max_size
        self._cache: dict[str, tuple[str, float]] = {}  # path -> (content, mtime)
        self._access_order: list[str] = []  # LRU tracking
    
    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for file path.
        
        Args:
            file_path: Path to file
            
        Returns:
            Cache key (normalized absolute path)
        """
        return str(file_path.resolve())
    
    def get(self, file_path: Path) -> Optional[str]:
        """Get file content from cache if available and fresh.
        
        Args:
            file_path: Path to file
            
        Returns:
            File content if cached and fresh, None otherwise
        """
        if not file_path.exists():
            return None
        
        cache_key = self._get_cache_key(file_path)
        current_mtime = file_path.stat().st_mtime
        
        if cache_key in self._cache:
            cached_content, cached_mtime = self._cache[cache_key]
            
            # Check if file has been modified
            if cached_mtime == current_mtime:
                # Update access order (LRU)
                if cache_key in self._access_order:
                    self._access_order.remove(cache_key)
                self._access_order.append(cache_key)
                logger.debug(f"Cache hit for {file_path}")
                return cached_content
            else:
                # File modified, remove from cache
                logger.debug(f"Cache invalidated for {file_path} (file modified)")
                del self._cache[cache_key]
                if cache_key in self._access_order:
                    self._access_order.remove(cache_key)
        
        return None
    
    def set(self, file_path: Path, content: str) -> None:
        """Cache file content.
        
        Args:
            file_path: Path to file
            content: File content to cache
        """
        if not file_path.exists():
            return
        
        cache_key = self._get_cache_key(file_path)
        mtime = file_path.stat().st_mtime
        
        # Evict oldest entry if cache is full
        if len(self._cache) >= self.max_size and cache_key not in self._cache:
            if self._access_order:
                oldest_key = self._access_order.pop(0)
                del self._cache[oldest_key]
                logger.debug(f"Cache evicted {oldest_key}")
        
        # Add to cache
        self._cache[cache_key] = (content, mtime)
        if cache_key in self._access_order:
            self._access_order.remove(cache_key)
        self._access_order.append(cache_key)
        
        logger.debug(f"Cached {file_path}")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._access_order.clear()
        logger.debug("File cache cleared")
    
    def invalidate(self, file_path: Path) -> None:
        """Invalidate cache entry for a specific file.
        
        Args:
            file_path: Path to file to invalidate
        """
        cache_key = self._get_cache_key(file_path)
        if cache_key in self._cache:
            del self._cache[cache_key]
            if cache_key in self._access_order:
                self._access_order.remove(cache_key)
            logger.debug(f"Cache invalidated for {file_path}")


# Global file cache instance
_file_cache: Optional[FileCache] = None


def get_file_cache() -> FileCache:
    """Get the global file cache instance.
    
    Returns:
        FileCache instance
    """
    global _file_cache
    if _file_cache is None:
        config = get_config()
        _file_cache = FileCache(max_size=config.cache_max_size)
    return _file_cache


def cached_read_file(file_path: Path, encoding: str = "utf-8") -> str:
    """Read file with caching.
    
    This function reads a file and caches its content. Subsequent calls
    with the same file path will return cached content if the file hasn't
    been modified.
    
    Args:
        file_path: Path to file to read
        encoding: File encoding (default: utf-8)
        
    Returns:
        File content as string
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    config = get_config()
    
    # If caching is disabled, read directly
    if not config.enable_file_caching:
        return file_path.read_text(encoding=encoding)
    
    # Try to get from cache
    cache = get_file_cache()
    cached_content = cache.get(file_path)
    
    if cached_content is not None:
        return cached_content
    
    # Read file and cache it
    content = file_path.read_text(encoding=encoding)
    cache.set(file_path, content)
    
    return content


def clear_file_cache() -> None:
    """Clear the global file cache."""
    cache = get_file_cache()
    cache.clear()


def invalidate_file_cache(file_path: Path) -> None:
    """Invalidate cache entry for a specific file.
    
    Args:
        file_path: Path to file to invalidate
    """
    cache = get_file_cache()
    cache.invalidate(file_path)

