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

"""Tool-grounded tools for MAS V2 workflow.

These tools are designed to work with TaskState and provide structured,
reliable operations for code generation workflows.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

from .models import ArtifactMetadata, TaskState

log = logging.getLogger(__name__)


# ============================================================================
# Repo Navigation Tools
# ============================================================================


class ListFilesInput(BaseModel):
    """Input schema for listing files in a directory."""

    directory: str = Field(
        default=".",
        description="Directory path to list (relative or absolute)",
    )
    recursive: bool = Field(
        default=False,
        description="Whether to list files recursively",
    )
    include_hidden: bool = Field(
        default=False,
        description="Whether to include hidden files",
    )


class ListFilesConfig(FunctionBaseConfig, name="list_files"):
    """Tool for listing files in a directory."""

    description: str = Field(
        default="List files in a directory. Supports recursive listing and filtering.",
        description="Description of the list files tool",
    )


@register_function(config_type=ListFilesConfig)
async def list_files_tool(config: ListFilesConfig, builder: Builder):
    """List files in a directory."""

    log.info("Initializing list files tool")

    async def _list_files(input_data: ListFilesInput) -> str:
        """List files in a directory."""
        log.info("Listing files in: %s", input_data.directory)

        try:
            dir_path = Path(input_data.directory)

            if not dir_path.exists():
                return f"Error: Directory does not exist: {input_data.directory}"

            if not dir_path.is_dir():
                return f"Error: Path is not a directory: {input_data.directory}"

            files = []
            if input_data.recursive:
                for file_path in dir_path.rglob("*"):
                    if not input_data.include_hidden and file_path.name.startswith("."):
                        continue
                    if file_path.is_file():
                        files.append(str(file_path.relative_to(dir_path)))
            else:
                for file_path in dir_path.iterdir():
                    if not input_data.include_hidden and file_path.name.startswith("."):
                        continue
                    if file_path.is_file():
                        files.append(file_path.name)
                    elif file_path.is_dir():
                        files.append(f"{file_path.name}/")

            files.sort()

            result = f"Found {len(files)} items in {dir_path.resolve()}:\n"
            for file in files:
                result += f"  - {file}\n"

            return result

        except Exception as e:
            error_msg = f"Error listing files in {input_data.directory}: {str(e)}"
            log.error(error_msg)
            return error_msg

    yield FunctionInfo.from_fn(
        _list_files,
        input_schema=ListFilesInput,
        description=config.description,
    )


# ============================================================================
# Code Search Tools
# ============================================================================


class SearchCodeInput(BaseModel):
    """Input schema for searching code patterns."""

    pattern: str = Field(description="Search pattern (regex supported)")
    directory: str = Field(
        default=".",
        description="Directory to search in",
    )
    file_extensions: Optional[List[str]] = Field(
        default=None,
        description="File extensions to search (e.g., ['.py', '.js'])",
    )


class SearchCodeConfig(FunctionBaseConfig, name="search_code"):
    """Tool for searching code patterns in files."""

    description: str = Field(
        default="Search for code patterns in files using regex.",
        description="Description of the search code tool",
    )


@register_function(config_type=SearchCodeConfig)
async def search_code_tool(config: SearchCodeConfig, builder: Builder):
    """Search for code patterns in files."""

    log.info("Initializing search code tool")

    async def _search_code(input_data: SearchCodeInput) -> str:
        """Search for code patterns."""
        log.info("Searching for pattern '%s' in %s", input_data.pattern, input_data.directory)

        try:
            import re

            dir_path = Path(input_data.directory)
            if not dir_path.exists():
                return f"Error: Directory does not exist: {input_data.directory}"

            pattern = re.compile(input_data.pattern)
            matches = []

            for file_path in dir_path.rglob("*"):
                if not file_path.is_file():
                    continue

                if input_data.file_extensions:
                    if file_path.suffix not in input_data.file_extensions:
                        continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                matches.append(
                                    {
                                        "file": str(file_path.relative_to(dir_path)),
                                        "line": line_num,
                                        "content": line.strip()[:100],
                                    }
                                )
                except Exception:
                    continue

            if not matches:
                return f"No matches found for pattern '{input_data.pattern}'"

            result = f"Found {len(matches)} matches for pattern '{input_data.pattern}':\n"
            for match in matches[:50]:  # Limit to 50 matches
                result += f"  {match['file']}:{match['line']}: {match['content']}\n"

            if len(matches) > 50:
                result += f"\n... and {len(matches) - 50} more matches"

            return result

        except Exception as e:
            error_msg = f"Error searching code: {str(e)}"
            log.error(error_msg)
            return error_msg

    yield FunctionInfo.from_fn(
        _search_code,
        input_schema=SearchCodeInput,
        description=config.description,
    )


# ============================================================================
# File Read Tool (for Worker: read file content before LLM edit)
# ============================================================================


class ReadFileInput(BaseModel):
    """Input schema for reading file content."""

    file_path: str = Field(
        description="Path to the file to read (relative to repo_root or absolute)",
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding to use",
    )
    max_size_mb: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum file size in MB to read",
    )


class ReadFileConfig(FunctionBaseConfig, name="read_file"):
    """Tool for reading file content. Used by Worker to pass context to LLM."""

    description: str = Field(
        default="Read content from a file. Use for code/edit workflows.",
        description="Description of the read file tool",
    )


@register_function(config_type=ReadFileConfig)
async def read_file_tool(config: ReadFileConfig, builder: Builder):
    """Read file content for Worker code generation."""

    log.info("Initializing read file tool")

    async def _read_file(input_data: ReadFileInput) -> str:
        """Read content from a file."""
        log.info("Reading file: %s", input_data.file_path)

        try:
            file_path = Path(input_data.file_path)

            if not file_path.exists():
                return f"Error: File not found: {input_data.file_path}"

            if not file_path.is_file():
                return f"Error: Path is not a file: {input_data.file_path}"

            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > input_data.max_size_mb:
                return (
                    f"Error: File too large: {file_size_mb:.2f}MB "
                    f"(max: {input_data.max_size_mb}MB)"
                )

            with open(
                file_path, "r", encoding=input_data.encoding, errors="replace"
            ) as f:
                content = f.read()

            abs_path = file_path.resolve()
            return f"""Path: {abs_path}
Size: {file_path.stat().st_size} bytes

Content:
{content}"""

        except Exception as e:
            error_msg = f"Error reading file {input_data.file_path}: {str(e)}"
            log.error(error_msg)
            return error_msg

    yield FunctionInfo.from_fn(
        _read_file,
        input_schema=ReadFileInput,
        description=config.description,
    )


# ============================================================================
# Execution Tools
# ============================================================================


class RunShellInput(BaseModel):
    """Input schema for running shell commands."""

    command: str = Field(description="Shell command to execute")
    working_directory: str = Field(
        default=".",
        description="Working directory for command execution",
    )
    timeout: int = Field(
        default=300,
        ge=1,
        le=3600,
        description="Timeout in seconds (1-3600)",
    )


class RunShellConfig(FunctionBaseConfig, name="run_shell"):
    """Tool for executing shell commands."""

    description: str = Field(
        default="Execute shell commands and return stdout/stderr. Use for tests, builds, linting, etc.",
        description="Description of the run shell tool",
    )


@register_function(config_type=RunShellConfig)
async def run_shell_tool(config: RunShellConfig, builder: Builder):
    """Execute shell commands."""

    log.info("Initializing run shell tool")

    async def _run_shell(input_data: RunShellInput) -> str:
        """Execute shell command."""
        log.info("Executing command: %s in %s", input_data.command, input_data.working_directory)

        try:
            work_dir = Path(input_data.working_directory)
            if not work_dir.exists():
                return f"Error: Working directory does not exist: {input_data.working_directory}"

            result = subprocess.run(
                input_data.command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=input_data.timeout,
            )

            output = f"Command: {input_data.command}\n"
            output += f"Exit code: {result.returncode}\n"
            output += f"Working directory: {work_dir.resolve()}\n\n"

            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"

            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"

            return output

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {input_data.timeout} seconds"
        except Exception as e:
            error_msg = f"Error executing command: {str(e)}"
            log.error(error_msg)
            return error_msg

    yield FunctionInfo.from_fn(
        _run_shell,
        input_schema=RunShellInput,
        description=config.description,
    )


class RunTestInput(BaseModel):
    """Input schema for running tests."""

    test_command: str = Field(
        default="pytest -v",
        description="Test command to execute (e.g., 'pytest', 'npm test', 'python -m pytest')",
    )
    working_directory: str = Field(
        default=".",
        description="Working directory for test execution",
    )
    timeout: int = Field(
        default=600,
        ge=1,
        le=3600,
        description="Timeout in seconds",
    )


class RunTestConfig(FunctionBaseConfig, name="run_test"):
    """Tool for running test suites."""

    description: str = Field(
        default="Run test suites (pytest, npm test, etc.) and return structured results.",
        description="Description of the run test tool",
    )


@register_function(config_type=RunTestConfig)
async def run_test_tool(config: RunTestConfig, builder: Builder):
    """Run test suites."""

    log.info("Initializing run test tool")

    async def _run_test(input_data: RunTestInput) -> str:
        """Run tests."""
        log.info("Running tests: %s in %s", input_data.test_command, input_data.working_directory)

        try:
            work_dir = Path(input_data.working_directory)
            if not work_dir.exists():
                return f"Error: Working directory does not exist: {input_data.working_directory}"

            result = subprocess.run(
                input_data.test_command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=input_data.timeout,
            )

            output = f"Test command: {input_data.test_command}\n"
            output += f"Exit code: {result.returncode}\n"
            output += f"Working directory: {work_dir.resolve()}\n\n"

            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"

            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"

            if "pytest" in input_data.test_command.lower() and result.returncode == 0:
                lines = result.stdout.split("\n")
                for line in lines:
                    if "passed" in line.lower() or "failed" in line.lower():
                        output += f"\nTest Summary: {line.strip()}\n"

            return output

        except subprocess.TimeoutExpired:
            return f"Error: Tests timed out after {input_data.timeout} seconds"
        except Exception as e:
            error_msg = f"Error running tests: {str(e)}"
            log.error(error_msg)
            return error_msg

    yield FunctionInfo.from_fn(
        _run_test,
        input_schema=RunTestInput,
        description=config.description,
    )


# ============================================================================
# Improved File Writing Tool (TaskState-aware)
# ============================================================================


class WriteFileInput(BaseModel):
    """Input schema for writing files with TaskState integration."""

    file_path: str = Field(description="Path where the file should be created (REQUIRED)")
    content: str = Field(description="Content to write to the file")
    create_directories: bool = Field(
        default=True,
        description="Whether to create parent directories if they don't exist",
    )
    encoding: str = Field(
        default="utf-8",
        description="File encoding to use",
    )

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path is provided and not empty."""
        if not v or not v.strip():
            raise ValueError("file_path is required and cannot be empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is not empty."""
        if not v or not v.strip():
            raise ValueError("content cannot be empty")
        return v


class WriteFileConfig(FunctionBaseConfig, name="write_file"):
    """Improved file writing tool with TaskState awareness."""

    description: str = Field(
        default="Write content to a file. REQUIRES explicit file_path. Updates TaskState artifacts.",
        description="Description of the write file tool",
    )


@register_function(config_type=WriteFileConfig)
async def write_file_tool(config: WriteFileConfig, builder: Builder):
    """Improved file writing tool."""

    log.info("Initializing write file tool")

    async def _write_file(input_data: WriteFileInput) -> str:
        """Write content to file."""
        log.info("Writing file: %s", input_data.file_path)

        try:
            file_path = Path(input_data.file_path)

            if ".." in str(file_path):
                return "Error: File path cannot contain '..' (parent directory references)"

            if input_data.create_directories:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                log.info("Created directories: %s", file_path.parent)

            with open(file_path, "w", encoding=input_data.encoding) as f:
                processed_content = (
                    input_data.content.replace("\\n", "\n")
                    .replace("\\t", "\t")
                    .replace("\\r", "\r")
                )
                f.write(processed_content)

            if not file_path.exists() or os.path.getsize(file_path) == 0:
                raise OSError(f"File not written correctly: {file_path}")

            abs_path = file_path.resolve()
            file_size = os.path.getsize(abs_path)

            log.info("Successfully wrote file: %s (%s bytes)", abs_path, file_size)

            return f"""File successfully written:
- Path: {abs_path}
- Size: {file_size} bytes
- Encoding: {input_data.encoding}

Note: Update TaskState.artifacts with this file's metadata."""

        except Exception as e:
            error_msg = f"Error writing file {input_data.file_path}: {str(e)}"
            log.error(error_msg)
            return error_msg

    yield FunctionInfo.from_fn(
        _write_file,
        input_schema=WriteFileInput,
        description=config.description,
    )
