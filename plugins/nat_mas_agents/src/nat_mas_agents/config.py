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

"""Configuration management for MAS workflow.

This module provides centralized configuration for file paths, settings, and
environment-specific configurations to replace hardcoded values throughout the codebase.
"""

import os
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class MASConfig(BaseModel):
    """Configuration for MAS workflow system.
    
    This class centralizes all configuration values including file paths,
    timeouts, retry settings, and feature flags. It replaces hardcoded
    values throughout the codebase.
    """
    
    # Directory paths
    output_dir: Path = Field(
        default=Path("output"),
        description="Base output directory for all generated artifacts"
    )
    doc_dir: Path = Field(
        default=Path("output/doc"),
        description="Directory for phase output documents"
    )
    
    # Workflow settings
    max_fix_iterations: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum number of QA-driven fix attempts after initial engineer run"
    )
    require_pass_before_integrator: bool = Field(
        default=True,
        description="If true, integrator phase only runs after QA passes"
    )
    
    # Timeout settings
    phase_timeout: float = Field(
        default=300.0,
        gt=0,
        description="Timeout in seconds for each phase execution (default: 5 minutes)"
    )
    
    # Feature flags
    enable_metrics: bool = Field(
        default=True,
        description="Enable metrics collection for workflow execution"
    )
    enable_file_caching: bool = Field(
        default=True,
        description="Enable file content caching for performance"
    )
    cache_max_size: int = Field(
        default=10,
        gt=0,
        description="Maximum number of files to cache"
    )
    
    # Retry settings
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of retries for agent calls"
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        gt=0,
        description="Exponential backoff factor for retries"
    )
    
    @field_validator('output_dir', 'doc_dir', mode='before')
    @classmethod
    def validate_paths(cls, v) -> Path:
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    @field_validator('doc_dir', mode='after')
    @classmethod
    def validate_doc_dir(cls, v: Path, info) -> Path:
        """Ensure doc_dir is within output_dir."""
        if 'output_dir' in info.data:
            output_dir = info.data['output_dir']
            # If doc_dir is relative, make it relative to output_dir
            if not v.is_absolute() and str(v).startswith('output'):
                return output_dir / "doc"
        return v
    
    # Computed properties for file paths
    @property
    def pm_output_path(self) -> Path:
        """Path to Product Manager output file."""
        return self.doc_dir / "pm_output.txt"
    
    @property
    def architect_output_path(self) -> Path:
        """Path to Architect output file."""
        return self.doc_dir / "architect_output.txt"
    
    @property
    def project_manager_output_path(self) -> Path:
        """Path to Project Manager output file."""
        return self.doc_dir / "project_manager_output.txt"
    
    @property
    def tester_output_path(self) -> Path:
        """Path to QA Tester output file."""
        return self.doc_dir / "tester_output.txt"
    
    @property
    def integrator_output_path(self) -> Path:
        """Path to Integrator output file."""
        return self.doc_dir / "integrator_output.txt"
    
    @property
    def architect_handoff_path(self) -> Path:
        """Path to Architect structured handoff JSON."""
        return self.doc_dir / "architect_handoff.json"
    
    @property
    def project_manager_handoff_path(self) -> Path:
        """Path to Project Manager structured handoff JSON."""
        return self.doc_dir / "project_manager_handoff.json"
    
    def get_project_output_dir(self, project_name: str) -> Path:
        """Get output directory for a specific project.
        
        Args:
            project_name: Name of the project (will be normalized to kebab-case)
            
        Returns:
            Path to project-specific output directory
        """
        normalized_name = normalize_project_name(project_name)
        return self.output_dir / normalized_name
    
    @classmethod
    def from_env(cls) -> "MASConfig":
        """Create configuration from environment variables.
        
        Environment variables:
        - MAS_OUTPUT_DIR: Base output directory (default: "output")
        - MAS_DOC_DIR: Document directory (default: "output/doc")
        - MAS_MAX_FIX_ITERATIONS: Max fix iterations (default: 2)
        - MAS_PHASE_TIMEOUT: Phase timeout in seconds (default: 300.0)
        - MAS_ENABLE_METRICS: Enable metrics (default: "true")
        - MAS_ENABLE_CACHE: Enable file caching (default: "true")
        - MAS_CACHE_MAX_SIZE: Cache max size (default: 10)
        - MAS_MAX_RETRIES: Max retries (default: 3)
        - MAS_RETRY_BACKOFF: Retry backoff factor (default: 2.0)
        
        Returns:
            MASConfig instance with values from environment
        """
        return cls(
            output_dir=Path(os.getenv("MAS_OUTPUT_DIR", "output")),
            doc_dir=Path(os.getenv("MAS_DOC_DIR", "output/doc")),
            max_fix_iterations=int(os.getenv("MAS_MAX_FIX_ITERATIONS", "2")),
            phase_timeout=float(os.getenv("MAS_PHASE_TIMEOUT", "300.0")),
            enable_metrics=os.getenv("MAS_ENABLE_METRICS", "true").lower() == "true",
            enable_file_caching=os.getenv("MAS_ENABLE_CACHE", "true").lower() == "true",
            cache_max_size=int(os.getenv("MAS_CACHE_MAX_SIZE", "10")),
            max_retries=int(os.getenv("MAS_MAX_RETRIES", "3")),
            retry_backoff_factor=float(os.getenv("MAS_RETRY_BACKOFF", "2.0")),
        )
    
    @classmethod
    def default(cls) -> "MASConfig":
        """Get default configuration.
        
        Returns:
            MASConfig with default values
        """
        return cls()
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.doc_dir.mkdir(parents=True, exist_ok=True)


# Global configuration instance
# Can be overridden by calling from_env() or creating a custom instance
_config: Optional[MASConfig] = None


def get_config() -> MASConfig:
    """Get the global MAS configuration.
    
    If no configuration has been set, creates one from environment variables
    or uses defaults.
    
    Returns:
        Current MASConfig instance
    """
    global _config
    if _config is None:
        _config = MASConfig.from_env()
        _config.ensure_directories()
    return _config


def set_config(config: MASConfig) -> None:
    """Set the global MAS configuration.
    
    Args:
        config: MASConfig instance to use globally
    """
    global _config
    _config = config
    _config.ensure_directories()


def reset_config() -> None:
    """Reset the global configuration to None (will use defaults on next get_config())."""
    global _config
    _config = None


def normalize_project_name(project_name: str) -> str:
    """Normalize project name to kebab-case for consistent folder naming.
    
    Converts any project name format (title case, spaces, etc.) to kebab-case
    (lowercase with hyphens). This ensures consistent folder naming across
    all phases of the workflow.
    
    Examples:
        "Fashion Marketplace Website" -> "fashion-marketplace-website"
        "fashion-marketplace-website" -> "fashion-marketplace-website"
        "MyProject" -> "myproject"
        "my_project" -> "my-project"
    
    Args:
        project_name: Project name in any format
        
    Returns:
        Normalized project name in kebab-case format
    """
    if not project_name:
        return "project_output"
    
    # Remove leading/trailing whitespace
    name = project_name.strip()
    
    # If already in kebab-case (lowercase with hyphens), return as-is
    if re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', name):
        return name
    
    # Replace spaces, underscores, and other separators with hyphens
    name = re.sub(r'[\s_]+', '-', name)
    
    # Convert to lowercase
    name = name.lower()
    
    # Remove any consecutive hyphens
    name = re.sub(r'-+', '-', name)
    
    # Remove leading/trailing hyphens
    name = name.strip('-')
    
    # Remove any non-alphanumeric characters except hyphens
    name = re.sub(r'[^a-z0-9-]', '', name)
    
    # If empty after normalization, return default
    if not name:
        return "project_output"
    
    return name

