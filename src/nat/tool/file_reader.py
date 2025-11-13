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

import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

log = logging.getLogger(__name__)


class FileReaderInput(BaseModel):
    """Input schema for file reader tool."""
    file_path: str = Field(description="Path to the file to read (relative or absolute)")
    encoding: str = Field(default="utf-8", description="File encoding to use")
    max_size_mb: int = Field(default=10, description="Maximum file size in MB to read (to prevent memory issues)")


class FileReaderConfig(FunctionBaseConfig, name="file_reader"):
    """
    Tool for reading content from files.
    Supports reading text files with size limits and encoding options.
    """
    description: str = Field(
        default="Tool for reading content from files. Can read text files with configurable encoding.",
        description="Description of the file reader tool"
    )


@register_function(config_type=FileReaderConfig)
async def file_reader_tool(config: FileReaderConfig, builder: Builder):
    """File reader tool that can read content from files."""
    
    log.info('Initializing file reader tool')
    
    async def _read_file(input_data: FileReaderInput) -> str:
        """Read content from a file."""
        log.info(f'Reading file: {input_data.file_path}')
        
        try:
            # Convert to Path object for easier manipulation
            file_path = Path(input_data.file_path)
            
            # Check if file exists
            if not file_path.exists():
                error_msg = f"File not found: {input_data.file_path}"
                log.error(error_msg)
                return error_msg
            
            # Check if it's a file (not directory)
            if not file_path.is_file():
                error_msg = f"Path is not a file: {input_data.file_path}"
                log.error(error_msg)
                return error_msg
            
            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > input_data.max_size_mb:
                error_msg = f"File too large to read: {file_size_mb:.2f}MB (max: {input_data.max_size_mb}MB)"
                log.error(error_msg)
                return error_msg
            
            # Read content from file
            with open(file_path, 'r', encoding=input_data.encoding) as f:
                content = f.read()
            
            # Get absolute path for response
            abs_path = file_path.resolve()
            file_size = file_path.stat().st_size
            
            log.info(f'Successfully read file: {abs_path} ({file_size} bytes)')
            
            return f"""File successfully read:
- Path: {abs_path}
- Size: {file_size} bytes
- Encoding: {input_data.encoding}

Content:
{content}"""
            
        except UnicodeDecodeError as e:
            error_msg = f"Error reading file {input_data.file_path}: Unable to decode with {input_data.encoding} encoding. {str(e)}"
            log.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error reading file {input_data.file_path}: {str(e)}"
            log.error(error_msg)
            return error_msg
    
    yield FunctionInfo.from_fn(
        _read_file,
        input_schema=FileReaderInput,
        description=config.description
    )

