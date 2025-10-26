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


class FileWriterInput(BaseModel):
    """Input schema for file writer tool."""
    file_path: str = Field(description="Path where the file should be created (relative or absolute)")
    content: str = Field(description="Content to write to the file")
    create_directories: bool = Field(default=True, description="Whether to create parent directories if they don't exist")
    encoding: str = Field(default="utf-8", description="File encoding to use")


class FileWriterConfig(FunctionBaseConfig, name="file_writer"):
    """
    Tool for writing content to files.
    Supports creating directories and writing text content to files.
    """
    description: str = Field(
        default="Tool for writing content to files. Can create directories and write text content.",
        description="Description of the file writer tool"
    )


@register_function(config_type=FileWriterConfig)
async def file_writer_tool(config: FileWriterConfig, builder: Builder):
    """File writer tool that can create files and directories."""
    
    log.info('Initializing file writer tool')
    
    async def _write_file(input_data: FileWriterInput) -> str:
        """Write content to a file."""
        log.info(f'Writing file: {input_data.file_path}')
        
        try:
            # Convert to Path object for easier manipulation
            file_path = Path(input_data.file_path)
            
            # Create parent directories if requested
            if input_data.create_directories:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                log.info(f'Created directories: {file_path.parent}')
            
            # Write content to file
            with open(file_path, 'w', encoding=input_data.encoding) as f:
                # Process escape sequences to convert \n to actual newlines
                processed_content = input_data.content.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                f.write(processed_content)
            
            # Get absolute path for response
            abs_path = file_path.resolve()
            file_size = os.path.getsize(abs_path)
            
            log.info(f'Successfully wrote file: {abs_path} ({file_size} bytes)')
            
            return f"""File successfully created:
- Path: {abs_path}
- Size: {file_size} bytes
- Encoding: {input_data.encoding}
- Content preview: {input_data.content[:100]}{'...' if len(input_data.content) > 100 else ''}"""
            
        except Exception as e:
            error_msg = f"Error writing file {input_data.file_path}: {str(e)}"
            log.error(error_msg)
            return error_msg
    
    yield FunctionInfo.from_fn(
        _write_file,
        input_schema=FileWriterInput,
        description=config.description
    )
